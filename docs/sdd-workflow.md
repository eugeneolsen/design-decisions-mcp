# Spec-Driven Development (SDD) Workflow

With Functional Decision Records (FDRs) fully integrated into the decision record system, Spec-Driven Development becomes your project's north star: write behavioral specifications first, then let AI read and enforce those specs throughout implementation and review.

This guide walks you through standing up SDD in a project, from documenting architectural decisions to writing feature specs that guide code.

---

## Phase 1: Project Foundation — Document Architectural Decisions

**Goal:** Establish project-wide guardrails that every feature must respect.

### Steps

1. **Initialize the project** — Run `design-decisions-mcp init` to scaffold:
   - `CLAUDE.md` — Engineering Conformance Protocol for your AI assistant
   - `.github/workflows/validate-decisions.yml` — Automatic validation on every push and PR
   - `.githooks/pre-commit` — Automatic validation before every commit

2. **Write Architectural Decisions (ADRs)** — For each known architectural choice, create a record in `docs/adr/`:
   - Use AI assistance: *"We chose X over Y for Z reason. Write an ADR for this decision."*
   - Capture the problem, the choice, and the constraints that teams must respect
   - Set `status: accepted` once the decision is approved

3. **Validate and commit** — Validation is automatic:
   - The pre-commit hook blocks invalid commits before they land
   - GitHub Actions validates on every push and PR
   - Use `design-decisions-mcp validate` only for a manual check mid-authoring, before staging

**Output:** `docs/adr/ADR-NNNN-<slug>.yaml` files that the MCP server surfaces to AI on every task.

---

## Phase 2: Feature Structure — Create Feature Directory Trees

**Goal:** For each known feature, create a home for its decision records co-located with the code.

### Recommended Layout

```
src/
  auth/
    fdr/
      FDR-0001-login-flow.yaml
    ddr/
      DDR-0001-session-design.yaml
    sdr/
      SDR-0001-token-security.yaml
  payments/
    fdr/
      FDR-0001-checkout-flow.yaml
    ddr/
      DDR-0001-idempotency.yaml
```

For projects without a `src/` code tree (pure docs repos, monorepos), use `features/<name>/fdr/` at the top level. The MCP server discovers any directory named `adr/`, `ddr/`, `sdr/`, `odr/`, `tdr/`, `pdr/`, or `fdr/` anywhere in the tree.

**Important:** Create the `fdr/` directory *before* any design directories. The spec must exist before design decisions can meaningfully reference it.

---

## Phase 3: Write Specs First — Functional Decision Records (FDRs)

**This is the "spec-driven" step.** Specs precede implementation and design.

For each feature, write one or more FDRs capturing:

- **Context** — User stories and problem statement
- **Acceptance Criteria** — Behavioral expectations in Given-When-Then form
- **API Contracts / State Machines** — Optional structured decision fields for complex interactions

### Example Prompt Pattern

> *"For the [feature] feature, write an FDR. Context: [user story]. Acceptance criteria: [Given X / When Y / Then Z]."*

### Example FDR

```yaml
id: FDR-0001
type: functional
title: Login flow returns OAuth2 token on success
date: "2026-06-30"
status: proposed

context: >
  Users need a secure way to authenticate. OAuth2 is our chosen standard
  (per ADR-0001). This FDR captures the expected login behavior.

decision:
  chosen_option: OAuth2 login flow
  justification: Industry-standard, secure, and integrates with our auth system.

consequences:
  acceptance_criteria:
    - "Given a valid user, when they POST to /auth/login with credentials, then they receive a 200 with a JWT."
    - "Given an invalid password, when they POST to /auth/login, then they receive 401."
    - "Given a non-existent user, when they POST to /auth/login, then they receive 401."
```

FDRs start with `status: proposed`. Once reviewed and agreed upon by the team, set `status: accepted`.

---

## Phase 4: Add Supporting Decision Records

Once FDRs are accepted, add the supporting records that explain *how* the spec will be met:

| Record | Purpose | Write when... |
|--------|---------|---------------|
| DDR | Design/implementation patterns | You have a non-obvious implementation choice |
| SDR | Security guardrails | The feature handles auth, data, or external APIs |
| ODR | Operations/infrastructure constraints | Deployment, scaling, or config requirements |
| TDR | Vendor/tool choices | You're picking a library, SDK, or service |
| PDR | Process/CI standards | Automation, migration, or release requirements |

These records reference the FDR they support. **Only add a record type if a genuine decision exists** — not every feature needs all six types.

### Record Lifecycle

All decision records follow the same lifecycle: `proposed → accepted → implemented → deprecated / superseded`

- Start each record with `status: proposed`
- Once reviewed and approved by the team, change to `status: accepted`
- Once the code is shipped, change to `status: implemented`
- If a record is no longer relevant, mark it `deprecated` or create a new record with `supersedes: <old-id>` and mark the old one `superseded`

The MCP server enforces accepted records; proposed records are guidance only.

---

## Phase 5: Implement Features Using the Decision Records

**This is where the workflow becomes "spec-driven" in practice.**

Once your FDRs and supporting records are accepted, prompt your AI coding agent to implement the feature:

> *"Implement the [feature] feature. The specs are in `docs/` and `src/[feature]/fdr/`. Start by reading the relevant FDR to understand the acceptance criteria."*

The AI agent will:
1. Discover the relevant FDRs and DDRs using the MCP tools
2. Read the acceptance criteria and design constraints
3. Write code guided by those specs
4. Validate the implementation against the acceptance criteria before submitting

The decision records become the project's executable specification — they are the source of truth that guides both implementation and code review.

---

## Phase 6: The SDD Loop — How AI Uses These Records

This is what makes the workflow "spec-driven" rather than just "well-documented":

1. **AI discovers** — Before touching code, AI calls `list_architecture_decisions` and finds the relevant FDR.
2. **AI reads the spec** — AI calls `fetch_architecture_decision` to load acceptance criteria, constraints, and design rationale.
3. **AI implements** — Guided by acceptance criteria, AI writes code that satisfies the spec.
4. **AI validates** — After implementing, AI re-reads the FDR acceptance criteria and verifies each Given-When-Then is covered.
5. **Human reviews** — PR review confirms both the spec and implementation are consistent.

This closes the loop: **the spec is the source of truth**. AI reads it before coding, and the same record governs code review.

---

## Phase 7: Marking Records as Implemented

Once the code satisfying a decision ships, update the record's status to `implemented`:

```yaml
status: implemented
```

The full lifecycle for FDRs and DDRs:

```
proposed → accepted → implemented → deprecated / superseded
```

ADRs, SDRs, ODRs, TDRs, and PDRs can also use `implemented` — but FDRs and DDRs are the primary candidates since they most directly govern code behavior.

---

## Phase 8: SDD Is an Iterative Process

SDD is not a one-time documentation exercise. Decision records have a built-in lifecycle (`proposed → accepted → implemented → deprecated → superseded`) that supports continuous refinement:

### New Information
If assumptions behind an FDR turn out to be wrong, update the record and reflect the change in its status or create a new superseding record.

### Changed Plans
When a design decision is reversed or replaced, create a new record with `supersedes: DDR-NNNN` and set the old record's status to `superseded`. The MCP server surfaces the new record automatically.

### Issues in Production
Operational incidents often reveal missing constraints. Add an SDR or ODR to capture what was learned and prevent recurrence.

### Evolving Features
FDRs can grow additional acceptance criteria as edge cases are discovered. Keep the record current; it remains the authoritative spec.

The pre-commit hook and GitHub Actions ensure that every change to any record is valid before it lands — so iteration is safe by default.

---

## Quick-Start Cheat Sheet

| Type | Prefix | Directory | Purpose |
|------|--------|-----------|---------|
| ADR | `ADR-` | `adr/` | Architecture Decision Records — major structural or technology choices |
| DDR | `DDR-` | `ddr/` | Design Decision Records — implementation patterns and conventions |
| SDR | `SDR-` | `sdr/` | Security Decision Records — security and compliance guardrails |
| ODR | `ODR-` | `odr/` | Operations Decision Records — infrastructure and deployment constraints |
| TDR | `TDR-` | `tdr/` | Technical/Product Decision Records — vendor and tool boundaries |
| PDR | `PDR-` | `pdr/` | Process Decision Records — automation and CI/CD standards |
| FDR | `FDR-` | `fdr/` | Functional Decision Records — behavioral specs and acceptance criteria |

**File format:** Pure YAML, co-located with the code it governs. Example: `src/auth/fdr/FDR-0001-login-flow.yaml`

**Validation:** Automatic on commit and push. Manual check: `design-decisions-mcp validate`

**Lifecycle:** `proposed → accepted → implemented → deprecated / superseded`

---

## Future Enhancement: Implementation Status Reporting

Once `implemented` is a standard status, the MCP server will expose a reporting tool (e.g., `list_unimplemented_decisions`) giving the team visibility into which accepted records still need code. This tool is in the roadmap.  

It is conceivable that more granular progress status could be added in the future.
