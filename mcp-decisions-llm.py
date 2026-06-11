import os
import re
import sys
import yaml
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Architectural Context Oracle")

# Path to your decisions directory
DECISIONS_DIR = os.path.join(".continue", "decisions")

def get_all_records():
    """Dynamically parses and reads available decision record headers."""
    records = {}
    if not os.path.isdir(DECISIONS_DIR):
        return records

    for filename in os.listdir(DECISIONS_DIR):
        if not filename.endswith(".md"):
            continue
            
        file_path = os.path.join(DECISIONS_DIR, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Regex to isolate the YAML front matter from the body
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if not match:
                continue
                
            front_matter_raw = match.group(1)
            body_content = match.group(2).strip()
            meta = yaml.safe_load(front_matter_raw) or {}
            
            # Identify standard ID string
            record_id = str(meta.get("id", filename.replace(".md", ""))).upper()
            
            records[record_id] = {
                "title": meta.get("title", "Untitled Decision"),
                "description": meta.get("description", "No description provided."),
                "tags": meta.get("tags", []),
                "body": body_content
            }
        except Exception as e:
            print(f"Skipping bad file {filename}: {e}", file=sys.stderr)
            
    return records

@mcp.tool()
def list_architecture_decisions() -> str:
    """
    Returns a lightweight registry of all available project ADRs and DDRs.
    Includes only IDs, titles, and descriptions. Does NOT contain the heavy bodies.
    Call this first to discover which architecture rules might apply to the current task.
    """
    records = get_all_records()
    if not records:
        return "No design decisions found in the .continue/decisions/ directory."
        
    output = ["=== ARCHITECTURAL REGISTRY ==="]
    for rid, data in records.items():
        output.append(
            f"ID: {rid}\n"
            f"Title: {data['title']}\n"
            f"Description: {data['description']}\n"
            f"Tags: {', '.join(data['tags'])}\n"
            f"---"
        )
        
    return "\n".join(output)

@mcp.tool()
def fetch_architecture_decision(decision_id: str) -> str:
    """
    Retrieves the complete body, conformance parameters, and context of a specific decision record by its ID.
    Call this ONLY after identifying a relevant ID from 'list_architecture_decisions'.
    
    Args:
        decision_id: The specific ID string (e.g., 'ADR-0024')
    """
    records = get_all_records()
    target_id = decision_id.strip().upper()
    
    if target_id not in records:
        return f"Error: Decision ID '{decision_id}' not found in the project directory."
        
    record = records[target_id]
    return (
        f"=== CONFORMANCE GUARDRAIL: {target_id} ===\n"
        f"Title: {record['title']}\n\n"
        f"Mandatory Rules & Body Context:\n{record['body']}"
    )

if __name__ == "__main__":
    mcp.run(transport="stdio")
