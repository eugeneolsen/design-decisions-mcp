import os
import sys
import yaml
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Architectural Context Oracle")

TYPE_DIRS = {"adr", "ddr", "sdr", "odr", "tdr", "pdr"}


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
