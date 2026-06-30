# Engineering Conformance Protocol

You are an engineering assistant subject to project architectural guardrails. To minimize token waste, do not guess design decisions or read filesystem directories manually. 

## The Two-Stage JIT Retrieval Loop
1. **Discovery**: Before editing code or creating files, call the `list_architecture_decisions` tool to review our project-wide decision indexes.
2. **LLM Evaluation**: Analyze the returned titles and descriptions against the active task using your semantic reasoning. 
3. **Payload Loading**: If you determine that any record applies to the task, immediately call `fetch_architecture_decision` using its specific ID to load its mandatory implementation rules before generating any code.
4. **Lifecycle Note**: Keep the index output as a stable baseline reference. Do not re-call the listing tool on continuous multi-turn coding queries unless your history undergoes an explicit `/compact` event or context wipe.

## Security Model

Decision records are scoped to **git-tracked files only by default**. This means:
- Records must be in allowed discovery roots (`docs/`, `src/`)
- Records must be tracked by git (not in `.gitignore`'d directories)
- Untracked/stashed files are excluded, even if they exist in the working directory

This ensures that decision records have passed the repository's commit/review process 
before they are treated as authoritative rules. If branch protection is enforced, 
git-tracked = approved by reviewers.

To validate uncommitted records during development, override with:
```bash
DESIGN_DECISIONS_MCP_GIT_ONLY=false design-decisions-mcp validate
```
