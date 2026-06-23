import json
import os
import stat
import sys
import yaml
import jsonschema
from importlib.metadata import version as _pkg_version
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Architectural Context Oracle")

TYPE_DIRS = {"adr", "ddr", "sdr", "odr", "tdr", "pdr"}

DECISION_RECORD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Unified Decision Record Schema (XDR)",
    "type": "object",
    "required": ["id", "type", "title", "date", "status", "context", "decision", "consequences"],
    "additionalProperties": False,
    "allOf": [
        {"if": {"properties": {"type": {"const": "architecture"}}}, "then": {"properties": {"id": {"pattern": "^ADR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "design"}}}, "then": {"properties": {"id": {"pattern": "^DDR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "operations"}}}, "then": {"properties": {"id": {"pattern": "^ODR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "security"}}}, "then": {"properties": {"id": {"pattern": "^SDR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "product"}}}, "then": {"properties": {"id": {"pattern": "^TDR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "process"}}}, "then": {"properties": {"id": {"pattern": "^PDR-[0-9]{4}$"}}}},
    ],
    "properties": {
        "id": {"type": "string", "description": "Unique identifier prefixed by domain type (e.g., ADR-0001, SDR-0022)"},
        "type": {
            "type": "string",
            "enum": ["architecture", "design", "operations", "security", "product", "process"],
            "description": "The specific domain category of the decision record.",
        },
        "title": {"type": "string", "minLength": 10, "description": "Clear, descriptive title of the decision."},
        "date": {"type": "string", "format": "date", "description": "The date the record was created or updated (YYYY-MM-DD)."},
        "status": {
            "type": "string",
            "enum": ["proposed", "accepted", "rejected", "deprecated", "superseded"],
            "description": "The current lifecycle state of the decision.",
        },
        "supersedes": {"type": "string", "pattern": "^[A-Z]{3}-[0-9]{4}$", "description": "The ID of an earlier record that this new decision replaces."},
        "meta": {
            "type": "object",
            "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        },
        "context": {"type": "string", "minLength": 20, "description": "The background problem statement and technical forces driving this decision."},
        "decision": {
            "type": "object",
            "required": ["chosen_option", "justification"],
            "properties": {
                "chosen_option": {"type": "string"},
                "justification": {"type": "string"},
            },
        },
        "consequences": {
            "type": "object",
            "required": [],
            "additionalProperties": False,
            "properties": {
                "enforced_constraints": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "description": "Explicit 'Do' or 'Do Not' constraint strings evaluated by the AI harness."},
                },
                "classified_consequences": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["impact", "description"],
                        "additionalProperties": False,
                        "properties": {
                            "impact": {"type": "string", "enum": ["good", "bad", "neutral"], "description": "The polarity of the consequence based on MADR industry conventions."},
                            "description": {"type": "string", "minLength": 5, "description": "The textual description of the consequence."},
                        },
                    },
                },
            },
        },
        "implementation_tasks": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 5, "description": "A transient, actionable checklist item required to put this decision into effect."},
            "description": "Optional ephemeral tasks or migration steps required to execute this change.",
        },
    },
}

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


def get_all_records():
    """Walks the project tree discovering .yaml files in any xDR type directory."""
    records = {}
    for dirpath, dirnames, filenames in os.walk("."):
        # Skip hidden directories (e.g. .git, .venv)
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if os.path.basename(dirpath) not in TYPE_DIRS:
            continue
        scope = os.path.relpath(os.path.dirname(dirpath), ".").replace("\\", "/")
        for filename in filenames:
            if not filename.endswith(".yaml"):
                continue
            file_path = os.path.join(dirpath, filename)
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
    """Validate xDR YAML files against the embedded schema. Returns True if all pass."""
    schema = DECISION_RECORD_SCHEMA

    if files:
        files_to_check = files
    else:
        files_to_check = []
        for dirpath, dirnames, filenames in os.walk("."):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            if os.path.basename(dirpath) in TYPE_DIRS:
                for filename in filenames:
                    if filename.endswith(".yaml"):
                        files_to_check.append(os.path.join(dirpath, filename))

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
