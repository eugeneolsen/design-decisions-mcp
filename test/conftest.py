import os
import pathlib

import pytest
import yaml


@pytest.fixture()
def tmp_project(tmp_path):
    """Redirect CWD into an isolated temp dir for filesystem-walking tests."""
    original = os.getcwd()
    original_env = os.environ.get("DESIGN_DECISIONS_MCP_ROOTS")
    os.chdir(tmp_path)
    # For tests, allow discovery from the root (.) to avoid test setup complexity
    os.environ["DESIGN_DECISIONS_MCP_ROOTS"] = "."
    yield tmp_path
    os.chdir(original)
    # Restore original env
    if original_env is None:
        os.environ.pop("DESIGN_DECISIONS_MCP_ROOTS", None)
    else:
        os.environ["DESIGN_DECISIONS_MCP_ROOTS"] = original_env


@pytest.fixture()
def minimal_valid_record():
    return {
        "id": "ADR-0001",
        "type": "architecture",
        "title": "Use something for something important",
        "date": "2026-01-01",
        "status": "accepted",
        "context": "We needed a way to do the thing that needed doing here.",
        "decision": {"chosen_option": "Option A", "justification": "It was better."},
        "consequences": {"enforced_constraints": ["Do use this approach."]},
    }


@pytest.fixture()
def write_yaml(tmp_project):
    def _write(rel_path: str, data: dict) -> pathlib.Path:
        p = tmp_project / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.dump(data), encoding="utf-8")
        return p

    return _write
