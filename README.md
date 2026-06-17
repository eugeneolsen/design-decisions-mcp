# Design Decision MCP Server

An MCP (Model Context Protocol) server that surfaces Architecture Decision Records (ADRs) and Design Decision Records (DDRs) to AI coding assistants as just-in-time architectural guardrails.

## Overview

This server acts as an *Architectural Context Oracle*: when an AI assistant is about to write or modify code, it can query this server to discover which architectural decisions are relevant to the task, then fetch the full rules for those decisions. This prevents the assistant from guessing at design intent or violating project-wide standards.

## Decision Records

Decision records live in two directories:

| Type | Path | Purpose |
|------|------|---------|
| ADR | `docs/adr/` | Architecture Decision Records — major structural or technology choices |
| DDR | `docs/ddr/` | Design Decision Records — implementation patterns and conventions |

> **Note:** Front matter fields and document formats for ADRs and DDRs are being finalized to meet industry standards. The structure below reflects the current minimum required schema.

### File Format

Each decision record is a Markdown file with a YAML front matter block:

```markdown
---
id: ADR-0001
title: Use PostgreSQL as the primary database
description: Establishes PostgreSQL as the sole relational store for all persistent data.
tags:
  - database
  - infrastructure
---

## Context
...

## Decision
...

## Consequences
...
```

**Required front matter fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier, e.g. `ADR-0001` or `DDR-0012` |
| `title` | string | Short human-readable name for the decision |
| `description` | string | One-sentence summary used for discovery |
| `tags` | list | One or more topic tags (non-empty) |

## MCP Tools

The server exposes two tools to AI clients:

### `list_architecture_decisions`

Returns a lightweight registry of all decision records — IDs, titles, descriptions, and tags only. Call this first to discover which records may apply to the current task.

### `fetch_architecture_decision(decision_id)`

Fetches the complete body of a specific record by its ID (e.g., `ADR-0001`). Call this only after identifying a relevant ID from the listing tool.

## Installation

> **Note:** Simplified packaging and installation is planned. Currently, setup requires the following manual steps.

**Prerequisites:** Python 3.13+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/eugeneolsen/design-decisions-mcp.git
cd design-decisions-mcp
uv sync
```

### Running the server

```bash
uv run mcp-decisions-llm.py
```

The server communicates over `stdio` and is intended to be launched by an MCP-compatible client (e.g., Claude Code, Continue, or another MCP host).

### Configuring your MCP client

Point your MCP client at the server script. Example for a `mcp.json`-style config:

```json
{
  "mcpServers": {
    "design-decisions": {
      "command": "uv",
      "args": ["run", "mcp-decisions-llm.py"],
      "cwd": "/path/to/design-decisions-mcp"
    }
  }
}
```

## AI Assistant Usage (CLAUDE.md)

The recommended two-stage retrieval pattern for AI assistants:

1. **Discover** — call `list_architecture_decisions` before writing or modifying code.
2. **Evaluate** — reason over the returned titles and descriptions against the active task.
3. **Load** — call `fetch_architecture_decision` for any record that applies.
4. **Cache** — keep the index as a stable baseline; do not re-fetch on every turn within the same context window.

## Validation

A GitHub Actions workflow runs on every push and pull request to `main` and `develop`. It validates that all decision records in the decisions directories have well-formed YAML front matter and all required fields.

```
.github/
  workflows/validate_decisions.yml   # CI workflow
  scripts/validate_decisions.py      # Validation script (run locally or in CI)
```

Run validation locally:

```bash
python .github/scripts/validate_decisions.py
```

Exit code `0` means all records passed; exit code `1` reports which files have errors.
