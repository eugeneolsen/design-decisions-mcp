import json
import os
import stat
import sys
import tomllib
import yaml
import jsonschema
from importlib.metadata import version as _pkg_version
from mcp.server.fastmcp import FastMCP
from design_decision_schema import DECISION_RECORD_SCHEMA

mcp = FastMCP("Architectural Context Oracle")

TYPE_DIRS = {"adr", "ddr", "sdr", "odr", "tdr", "pdr"}
VENDOR_DIRS = {"node_modules", "vendor", "site-packages", ".venv", "venv", "env", ".git", "__pycache__", ".pytest_cache", "dist", "build"}

GITHUB_ACTIONS_WORKFLOW = """\
name: Architecture Records Conformance Check

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  validate-decisions:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v6

      - name: Validate Decision Records
        run: uvx --from git+https://github.com/eugeneolsen/design-decisions-mcp.git design-decisions-mcp validate
"""

PRE_COMMIT_HOOK = """\
#!/bin/sh
# Validate xDR decision records before committing.
# Installed by: design-decisions-mcp init
set -e

design-decisions-mcp validate
"""


def _load_from_pyproject():
    """Load discovery configuration from pyproject.toml if present."""
    if not os.path.exists("pyproject.toml"):
        return {}, False
    try:
        with open("pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        tool_config = pyproject.get("tool", {}).get("design-decisions-mcp", {})
        roots = tool_config.get("discovery-roots", [])
        git_only = tool_config.get("git-tracked-only", False)
        return roots if isinstance(roots, list) else [], git_only
    except Exception as e:
        print(f"Warning: Could not read pyproject.toml: {e}", file=sys.stderr)
    return [], False


def _get_allowed_roots():
    """
    Determine allowed discovery roots with precedence:
    1. DESIGN_DECISIONS_MCP_ROOTS env var (colon-separated)
    2. pyproject.toml [tool.design-decisions-mcp] discovery-roots
    3. Default: ["docs", "src"]
    """
    # Check environment variable
    env_roots = os.environ.get("DESIGN_DECISIONS_MCP_ROOTS")
    if env_roots:
        return [r.strip() for r in env_roots.split(":") if r.strip()]

    # Check pyproject.toml
    toml_roots, _ = _load_from_pyproject()
    if toml_roots:
        return toml_roots

    # Default
    return ["docs", "src"]


def _should_use_git_tracked_only():
    """
    Determine if discovery should be restricted to git-tracked files.
    Precedence:
    1. DESIGN_DECISIONS_MCP_GIT_ONLY env var (set to 'true' or '1')
    2. pyproject.toml [tool.design-decisions-mcp] git-tracked-only
    3. Default: False
    """
    # Check environment variable
    env_git_only = os.environ.get("DESIGN_DECISIONS_MCP_GIT_ONLY")
    if env_git_only:
        return env_git_only.lower() in ("true", "1", "yes")

    # Check pyproject.toml
    _, toml_git_only = _load_from_pyproject()
    return toml_git_only


def _get_git_tracked_files():
    """
    Get the set of files tracked by git. Returns None if not in a git repo.
    """
    try:
        import subprocess
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        # Convert to absolute paths and normalize
        return {os.path.abspath(line.strip()) for line in result.stdout.splitlines() if line.strip()}
    except Exception:
        return None


def _is_git_tracked(file_path, git_tracked_set):
    """Check if a file is in the git-tracked set."""
    abs_path = os.path.abspath(file_path)
    return abs_path in git_tracked_set


def _should_skip_dir(dirname):
    """Check if a directory should be skipped (vendor, hidden, etc.)."""
    if dirname.startswith("."):
        return True
    if dirname in VENDOR_DIRS:
        return True
    return False


def get_all_records():
    """
    Walks allowed discovery roots discovering .yaml files in any xDR type directory.
    Skips vendor and hidden directories at all levels.
    Optionally restricts to git-tracked files only.
    """
    records = {}
    allowed_roots = _get_allowed_roots()
    use_git_tracked_only = _should_use_git_tracked_only()
    git_tracked_files = None

    if use_git_tracked_only:
        git_tracked_files = _get_git_tracked_files()
        if git_tracked_files is None:
            print(
                "Warning: git-tracked-only mode enabled but not in a git repository. "
                "Discovery will be skipped.",
                file=sys.stderr,
            )
            return records

    for root in allowed_roots:
        if not os.path.isdir(root):
            continue

        for dirpath, dirnames, filenames in os.walk(root):
            # Skip vendor and hidden directories
            dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]

            if os.path.basename(dirpath) not in TYPE_DIRS:
                continue

            scope = os.path.relpath(os.path.dirname(dirpath), ".").replace("\\", "/")
            for filename in filenames:
                if not filename.endswith(".yaml"):
                    continue
                file_path = os.path.join(dirpath, filename)

                # Check git-tracked status if enabled
                if use_git_tracked_only and not _is_git_tracked(file_path, git_tracked_files):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if not data or not isinstance(data, dict):
                        continue
                    record_id = str(data.get("id", "")).upper()
                    if not record_id:
                        continue
                    scoped_key = f"{scope}/{record_id}"
                    records[scoped_key] = {
                        "type": data.get("type", ""),
                        "title": data.get("title", "Untitled Decision"),
                        "context": data.get("context", ""),
                        "tags": (data.get("meta") or {}).get("tags", []),
                        "raw": data,
                    }
                except Exception as e:
                    print(f"Skipping {file_path}: {e}", file=sys.stderr)

    return records


@mcp.tool()
def list_architecture_decisions() -> str:
    """
    Returns a lightweight registry of all available project decision records (ADRs, DDRs, SDRs, etc.).
    Includes only the scoped ID, type, title, a short context preview, and tags.
    Does NOT load full record bodies — call fetch_architecture_decision for that.
    Call this first to discover which records might apply to the current task.

    Scoped IDs use the format: {relative-path-to-parent}/{RECORD-ID}
    Example: services/billing-service/DDR-0001
    """
    records = get_all_records()
    if not records:
        return "No decision records found. Place .yaml files in any adr/, ddr/, sdr/, odr/, tdr/, or pdr/ directory."

    output = ["=== ARCHITECTURAL REGISTRY ==="]
    for scoped_key, data in sorted(records.items()):
        context_preview = data["context"][:120] + "..." if len(data["context"]) > 120 else data["context"]
        output.append(
            f"ID: {scoped_key}\n"
            f"Type: {data['type']}\n"
            f"Title: {data['title']}\n"
            f"Context: {context_preview}\n"
            f"Tags: {', '.join(data['tags'])}\n"
            f"---"
        )

    return "\n".join(output)


@mcp.tool()
def fetch_architecture_decision(decision_id: str) -> str:
    """
    Retrieves the complete content of a specific decision record by its scoped ID.
    Call this ONLY after identifying a relevant ID from list_architecture_decisions.

    Args:
        decision_id: The scoped ID string returned by list_architecture_decisions.
                     Format: {relative-path-to-parent}/{RECORD-ID}
                     Example: 'services/billing-service/DDR-0001' or 'docs/ADR-0001'
    """
    records = get_all_records()
    target_key = decision_id.strip()

    if target_key not in records:
        return f"Error: Decision '{decision_id}' not found. Use list_architecture_decisions to see valid IDs."

    record = records[target_key]
    return (
        f"=== CONFORMANCE GUARDRAIL: {target_key} ===\n"
        f"Title: {record['title']}\n\n"
        f"Full Record:\n{yaml.dump(record['raw'], default_flow_style=False, allow_unicode=True, sort_keys=False)}"
    )


def _validate_single_file(file_path, schema):
    """Validate one YAML file against schema. Returns True if valid."""
    if not file_path.endswith(".yaml"):
        return True
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            print(f"ERROR: {file_path} is empty or could not be parsed.")
            return False
        jsonschema.validate(instance=data, schema=schema)
        print(f"PASSED: {file_path}")
        return True
    except jsonschema.ValidationError as e:
        print(f"ERROR: {file_path} — {e.message}")
        return False
    except jsonschema.SchemaError as e:
        print(f"SCHEMA ERROR: {e.message}")
        return False
    except Exception as e:
        print(f"CRITICAL: {file_path} — {e}")
        return False


def validate_decisions(files=None):
    """
    Validate xDR YAML files against the embedded schema. Returns True if all pass.
    Optionally restricts to git-tracked files only.
    """
    schema = DECISION_RECORD_SCHEMA

    if files:
        files_to_check = files
    else:
        files_to_check = []
        allowed_roots = _get_allowed_roots()
        use_git_tracked_only = _should_use_git_tracked_only()
        git_tracked_files = None

        if use_git_tracked_only:
            git_tracked_files = _get_git_tracked_files()
            if git_tracked_files is None:
                print(
                    "Warning: git-tracked-only mode enabled but not in a git repository. "
                    "Validation will be skipped.",
                    file=sys.stderr,
                )
                return True

        for root in allowed_roots:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
                if os.path.basename(dirpath) in TYPE_DIRS:
                    for filename in filenames:
                        if filename.endswith(".yaml"):
                            file_path = os.path.join(dirpath, filename)

                            # Check git-tracked status if enabled
                            if use_git_tracked_only and not _is_git_tracked(file_path, git_tracked_files):
                                continue

                            files_to_check.append(file_path)

    if not files_to_check:
        print("No decision record files found.")
        return True

    has_errors = False
    for file_path in files_to_check:
        if not _validate_single_file(file_path, schema):
            has_errors = True

    if has_errors:
        print("\nValidation failed. Fix the errors above before committing.")

    return not has_errors


def _init_github_actions_workflow():
    """Create .github/workflows/validate-decisions.yml in the current project."""
    workflow_dir = os.path.join(".github", "workflows")
    workflow_path = os.path.join(workflow_dir, "validate-decisions.yml")

    if os.path.exists(workflow_path):
        print(f"{workflow_path} already exists, skipping")
        return

    os.makedirs(workflow_dir, exist_ok=True)
    with open(workflow_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(GITHUB_ACTIONS_WORKFLOW)
    print(f"Created {workflow_path}")


def _init_pre_commit_hook():
    """Create .githooks/pre-commit and configure git to use it."""
    hooks_dir = ".githooks"
    hook_path = os.path.join(hooks_dir, "pre-commit")

    os.makedirs(hooks_dir, exist_ok=True)

    if os.path.exists(hook_path):
        print(f"{hook_path} already exists, skipping")
    else:
        with open(hook_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(PRE_COMMIT_HOOK)
        os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Created {hook_path}")

    exit_code = os.system("git config core.hooksPath .githooks")
    if exit_code == 0:
        print("Configured git to use .githooks (core.hooksPath = .githooks)")
    else:
        print("WARNING: Could not run 'git config core.hooksPath .githooks'. Run it manually.", file=sys.stderr)


def init_project():
    """Initialize current project with decision records setup."""
    claude_md_path = "CLAUDE.md"
    conformance_protocol = """## Engineering Conformance Protocol

Before editing code or creating files, call `list_architecture_decisions` to discover
applicable guardrails. Fetch records that apply with `fetch_architecture_decision`.
Do not re-call the listing tool within the same context window unless your history
undergoes an explicit /compact event or context wipe (e.g. /clear).
"""

    # Check if file exists and already has the protocol
    if os.path.exists(claude_md_path):
        with open(claude_md_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "Engineering Conformance Protocol" in content:
            print(f"{claude_md_path} already contains the Engineering Conformance Protocol")
        else:
            # Append to existing file
            with open(claude_md_path, "a", encoding="utf-8") as f:
                f.write("\n" + conformance_protocol)
            print(f"Updated {claude_md_path} with Engineering Conformance Protocol")
    else:
        # Create new file
        with open(claude_md_path, "w", encoding="utf-8") as f:
            f.write("# Project CLAUDE.md\n\n" + conformance_protocol)
        print(f"Created {claude_md_path} with Engineering Conformance Protocol")

    _init_github_actions_workflow()
    _init_pre_commit_hook()


def main():
    if "init" in sys.argv:
        init_project()
    elif "validate" in sys.argv:
        specific_files = [arg for arg in sys.argv[2:] if arg.endswith(".yaml")]
        passed = validate_decisions(files=specific_files if specific_files else None)
        sys.exit(0 if passed else 1)
    elif "--version" in sys.argv or "-V" in sys.argv:
        print(_pkg_version("design-decisions-mcp"))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
