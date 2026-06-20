# Design Decision MCP Server

An MCP (Model Context Protocol) server that surfaces Architecture Decision Records (ADRs) and Design Decision Records (DDRs) to AI coding assistants as just-in-time architectural guardrails.

## Overview

This server acts as an *Architectural Context Oracle*: when an AI assistant is about to write or modify code, it can query this server to discover which architectural decisions are relevant to the task, then fetch the full rules for those decisions. This prevents the assistant from guessing at design intent or violating project-wide standards.

## Decision Records

Decision records are stored as pure YAML files and **co-located with the code they govern**. Any directory named `adr/`, `ddr/`, `sdr/`, `odr/`, `tdr/`, or `pdr/` anywhere in the project tree is a valid record container.

| Type | Prefix | Purpose |
|------|--------|---------|
| ADR | `ADR-` | Architecture Decision Records — major structural or technology choices |
| DDR | `DDR-` | Design Decision Records — implementation patterns and conventions |
| SDR | `SDR-` | Security Decision Records — security and compliance guardrails |
| ODR | `ODR-` | Operations Decision Records — infrastructure and deployment constraints |
| TDR | `TDR-` | Technical/Product Decision Records — vendor and tool boundaries |
| PDR | `PDR-` | Process Decision Records — automation and CI/CD standards |

**Examples:**
- `docs/adr/ADR-0001-microservices-split.yaml` → scoped ID: `docs/ADR-0001`
- `services/billing/ddr/DDR-0001-stripe-idempotency.yaml` → scoped ID: `services/billing/DDR-0001`

### File Format

Each decision record is a pure YAML file. The schema is defined in `docs/decision-record-schema.json`.

**Example:**

```yaml
id: ADR-0001
type: architecture
title: Use PostgreSQL as the primary database
date: "2026-06-19"
status: accepted

meta:
  tags:
    - database
    - infrastructure

context: |
  The application requires a relational database to handle complex queries
  and ACID transactions. PostgreSQL was chosen over MySQL and commercial
  options based on maturity, licensing, and operator familiarity.

decision:
  chosen_option: PostgreSQL as the sole relational store
  justification: >
    PostgreSQL offers strong ACID guarantees, JSON support, and no licensing
    restrictions. The team has production experience with it at scale.

consequences:
  enforced_constraints:
    - "Do store all relational data in PostgreSQL."
    - "Do NOT use document databases for transactional data."
  
  classified_consequences:
    - impact: good
      description: ACID guarantees eliminate entire classes of data corruption bugs.
    - impact: good
      description: Team expertise reduces operational risk.
    - impact: bad
      description: Scaling PostgreSQL horizontally requires careful sharding strategy.
```

**Required fields:** `id`, `type`, `title`, `date`, `status`, `context`, `decision`, `consequences`

See `docs/decision-record-schema.json` for the complete schema definition and optional fields.

## MCP Tools

The server exposes two tools to AI clients:

### `list_architecture_decisions()`

Returns a lightweight registry of all decision records discovered in the project tree. For each record, returns:
- **Scoped ID** (e.g., `docs/ADR-0001` or `services/billing/DDR-0001`)
- **Type** (architecture, design, security, operations, product, process)
- **Title**
- **Context preview** (first 120 characters)
- **Tags**

Call this first to discover which records may apply to the current task.

### `fetch_architecture_decision(scoped_id)`

Fetches the complete YAML content of a specific record by its scoped ID. Arguments:
- `scoped_id`: The path-qualified ID returned by `list_architecture_decisions`, e.g., `docs/ADR-0001` or `services/billing/DDR-0001`

Call this only after identifying a relevant ID from the listing tool. Returns the full record including `enforced_constraints` and detailed consequences.

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
uv run python mcp-decisions-llm.py
```

The server communicates over `stdio` and is intended to be launched by an MCP-compatible client (e.g., Claude Code, Continue, or another MCP host).

### Configuring your MCP client

Point your MCP client at the server script. Example for a `.mcp.json`-style config (e.g., Claude Code on Windows):

```json
{
  "mcpServers": {
    "decision-memory": {
      "type": "stdio",
      "command": ".\\venv\\Scripts\\python.exe",
      "args": ["mcp-decisions-llm.py"]
    }
  }
}
```

Or with `uv` directly:

```json
{
  "mcpServers": {
    "decision-memory": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "mcp-decisions-llm.py"]
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

A GitHub Actions workflow runs on every push and pull request to `main` and `develop`. It validates that all decision records conform to `docs/decision-record-schema.json` using `jsonschema`.

```
.github/
  workflows/validate_decisions.yml   # CI workflow (runs on push/PR)
  scripts/validate_decisions.py      # Validation script (runs locally or in CI)
```

Run validation locally:

```bash
uv run python .github/scripts/validate_decisions.py
```

Or validate a specific file:

```bash
uv run python .github/scripts/validate_decisions.py docs/adr/ADR-0001-my-decision.yaml
```

Exit code `0` means all records passed; exit code `1` reports validation errors. The validator walks the entire project tree searching for `.yaml` files in any `adr/`, `ddr/`, `sdr/`, `odr/`, `tdr/`, or `pdr/` directory.
