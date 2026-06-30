# Design Decision MCP Server

An MCP (Model Context Protocol) server that surfaces decision records (ADRs, DDRs, SDRs, ODRs, TDRs, PDRs, FDRs) to AI coding assistants as just-in-time architectural guardrails. Enables Spec-Driven Development (SDD) through Functional Decision Records that capture behavioral specifications.  

More simply stated, this MCP server turns the types of decision records listed below into something very similar to agent Skills.

## Overview

This server acts as an *Architectural Context Oracle*: when an AI assistant is about to write or modify code, it can query this server to discover which architectural decisions are relevant to the task, then fetch the full rules for those decisions. This prevents the assistant from guessing at design intent or violating project-wide standards.

**Spec-Driven Development (SDD):** The server enables SDD workflows through Functional Decision Records (FDRs), which capture behavioral specifications — acceptance criteria, API contracts, and state machines — alongside design rationale. This allows teams to write executable specifications that guide implementation and validation before code is written.

## Decision Records

Decision records are stored as pure YAML files and **co-located with the code they govern**. Any directory named `adr/`, `ddr/`, `sdr/`, `odr/`, `tdr/`, `pdr/`, or `fdr/` anywhere in the project tree is a valid record container.

| Type | Prefix | Purpose |
|------|--------|---------|
| ADR | `ADR-` | Architecture Decision Records — major structural or technology choices |
| DDR | `DDR-` | Design Decision Records — implementation patterns and conventions |
| SDR | `SDR-` | Security Decision Records — security and compliance guardrails |
| ODR | `ODR-` | Operations Decision Records — infrastructure and deployment constraints |
| TDR | `TDR-` | Technical/Product Decision Records — vendor and tool boundaries |
| PDR | `PDR-` | Process Decision Records — automation and CI/CD standards |
| FDR | `FDR-` | Functional Decision Records — behavioral specifications and acceptance criteria for Spec-Driven Development |

**Examples:**
- `docs/adr/ADR-0001-microservices-split.yaml` → scoped ID: `docs/ADR-0001`
- `services/billing/ddr/DDR-0001-stripe-idempotency.yaml` → scoped ID: `services/billing/DDR-0001`

### File Format

Each decision record is a pure YAML file. The schema is defined in `design_decision_schema.py`.

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

See `design_decision_schema.py` for the complete schema definition and optional fields.

## MCP Tools

The server exposes two tools to AI clients:

### `list_architecture_decisions()`

Returns a lightweight registry of all decision records discovered in the project tree. For each record, returns:
- **Scoped ID** (e.g., `docs/ADR-0001` or `services/billing/DDR-0001`)
- **Type** (architecture, design, security, operations, product, process, functional)
- **Title**
- **Context preview** (first 120 characters)
- **Tags**

Call this first to discover which records may apply to the current task.

### `fetch_architecture_decision(scoped_id)`

Fetches the complete YAML content of a specific record by its scoped ID. Arguments:
- `scoped_id`: The path-qualified ID returned by `list_architecture_decisions`, e.g., `docs/ADR-0001` or `services/billing/DDR-0001`

Call this only after identifying a relevant ID from the listing tool. Returns the full record including `enforced_constraints` and detailed consequences.

## Installation

### Global Install (Recommended)

Install once per machine, and every Claude Code session automatically has access to decision records across all projects.

**Prerequisites:** [uv](https://docs.astral.sh/uv/) (Python 3.13+ is installed as a dependency)

**1. Install globally:**

```bash
uv tool install git+https://github.com/eugeneolsen/design-decisions-mcp.git
```

**2. Add to `~/.claude/settings.json`:**

```json
{
  "mcpServers": {
    "decision-memory": {
      "type": "stdio",
      "command": "design-decisions-mcp"
    }
  }
}
```

That's it. Every Claude Code session on that machine will now have the `list_architecture_decisions` and `fetch_architecture_decision` tools available.

**Alternative: Using `uvx` (no persistent install)**

For teams that prefer not to install permanently:

```json
{
  "mcpServers": {
    "decision-memory": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/eugeneolsen/design-decisions-mcp.git", "design-decisions-mcp"]
    }
  }
}
```

This fetches and runs the server on first use, with no persistent installation.

### AI Assistant Instructions

Append the following to `~/.claude/CLAUDE.md` (or to your project's `CLAUDE.md` if you prefer per-project setup):

```markdown
## Engineering Conformance Protocol

Before editing code or creating files, call `list_architecture_decisions` to discover
applicable guardrails. Fetch records that apply with `fetch_architecture_decision`.
Do not re-call the listing tool within the same context window unless your history
undergoes an explicit /compact event or context wipe (e.g. /clear).
```

### Per-Project Setup (Optional)

To initialize a project with automatic validation, run once in the project root:

```bash
design-decisions-mcp init
```

This will set up:
1. **`CLAUDE.md`** — Engineering Conformance Protocol for the project's AI assistant
2. **`.github/workflows/validate-decisions.yml`** — Automatic validation on every push and pull request (with pinned action versions)
3. **`.githooks/pre-commit`** — Automatic validation before every commit

**Hook Configuration Safety:** The init command detects and respects existing `core.hooksPath` configurations:
- If `core.hooksPath` is not set, it will be configured to use `.githooks`
- If `core.hooksPath` is already set to `.githooks`, the setup is skipped (already correct)
- If `core.hooksPath` is set to a different directory (e.g., `.husky`, `lefthook`), a warning is printed and the existing configuration is preserved. You must manually switch if desired:
  ```bash
  git config core.hooksPath .githooks
  ```

All setup is idempotent; it's safe to re-run `init` at any time. Existing developer hook setups are never silently clobbered.

### Development/Local Setup

If you're developing this project or running it locally without a global install:

**Prerequisites:** Python 3.13+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/eugeneolsen/design-decisions-mcp.git
cd design-decisions-mcp
uv sync          # runtime dependencies only
uv sync --group dev  # + pytest and pytest-mock for running tests
```

**Run the server:**

```bash
uv run python mcp_decisions_llm.py
```

**Run the tests:**

```bash
uv run pytest
```

**Local MCP configuration:**

```json
{
  "mcpServers": {
    "decision-memory": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "mcp_decisions_llm.py"]
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

Decision records are validated against the schema defined in `design_decision_schema.py` using the `jsonschema` library.

### Automatic Validation (After `design-decisions-mcp init`)

Once you've run `design-decisions-mcp init` in your project, validation happens automatically:

- **Before every commit** — Pre-commit hook blocks commits with invalid records
- **On every push/PR** — GitHub Actions workflow validates all records in CI

### Manual Validation

Validate all records in the current project:

```bash
design-decisions-mcp validate
```

Or validate specific files:

```bash
design-decisions-mcp validate docs/adr/ADR-0001.yaml services/billing/ddr/DDR-0001.yaml
```

Exit code `0` means all records passed; exit code `1` reports validation errors. The validator walks the entire project tree searching for `.yaml` files in any `adr/`, `ddr/`, `sdr/`, `odr/`, `tdr/`, `pdr/`, or `fdr/` directory.

### CI/CD Setup

The `design-decisions-mcp init` command automatically creates `.github/workflows/validate-decisions.yml`, which runs on every push and pull request. 

**Security:** The generated workflow is hardened against supply-chain attacks:

- **GitHub Actions pinned to commit SHAs** — not mutable major-version tags
  - `actions/checkout` pinned to a specific commit
  - `astral-sh/setup-uv` pinned to a specific commit
  - Comments indicate which version (e.g., `# v4.2.0`)

- **Tool version pinned** — the `uvx --from` command includes `@v{version}`, not `@main`
  - Teams running `init` with v0.1.0 installed get `@v0.1.0` pinned
  - No automatic upgrades; teams control when to update
  - Protects against compromised `main` branch

Example generated workflow:
```yaml
uses: actions/checkout@d632683dd7b4114ad314bca15554477dd762a938  # v4.2.0
uses: astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e  # v6.8.0

run: uvx --from git+https://github.com/eugeneolsen/design-decisions-mcp.git@v0.1.0 design-decisions-mcp validate
```

This ensures validation works even for projects that don't have the tool installed permanently, while maintaining supply-chain security through pinned versions.

## License

This project is licensed under the [MIT License](LICENSE.md).
See the [LICENSE.md](LICENSE.md) file for details.
