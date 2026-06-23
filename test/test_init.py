import os
import stat

import pytest

from mcp_decisions_llm import (
    _init_github_actions_workflow,
    _init_pre_commit_hook,
    init_project,
    GITHUB_ACTIONS_WORKFLOW,
    PRE_COMMIT_HOOK,
)


class TestInitGithubActionsWorkflow:
    def test_creates_workflow_file(self, tmp_project):
        _init_github_actions_workflow()
        workflow_path = tmp_project / ".github" / "workflows" / "validate-decisions.yml"
        assert workflow_path.exists()

    def test_workflow_file_content(self, tmp_project):
        _init_github_actions_workflow()
        workflow_path = tmp_project / ".github" / "workflows" / "validate-decisions.yml"
        assert workflow_path.read_text() == GITHUB_ACTIONS_WORKFLOW

    def test_idempotent_does_not_overwrite(self, tmp_project):
        _init_github_actions_workflow()
        workflow_path = tmp_project / ".github" / "workflows" / "validate-decisions.yml"
        custom_content = "custom content"
        workflow_path.write_text(custom_content)
        _init_github_actions_workflow()
        assert workflow_path.read_text() == custom_content

    def test_prints_skip_message_when_exists(self, tmp_project, capsys):
        _init_github_actions_workflow()
        _init_github_actions_workflow()
        captured = capsys.readouterr()
        assert "already exists, skipping" in captured.out

    def test_creates_parent_directories(self, tmp_project):
        _init_github_actions_workflow()
        assert (tmp_project / ".github").exists()
        assert (tmp_project / ".github" / "workflows").exists()


class TestInitPreCommitHook:
    def test_creates_hook_file(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm.os.system", return_value=0)
        _init_pre_commit_hook()
        hook_path = tmp_project / ".githooks" / "pre-commit"
        assert hook_path.exists()

    def test_hook_file_content(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm.os.system", return_value=0)
        _init_pre_commit_hook()
        hook_path = tmp_project / ".githooks" / "pre-commit"
        assert hook_path.read_text() == PRE_COMMIT_HOOK

    @pytest.mark.skipif(os.name == "nt", reason="Windows does not honor Unix execute bits")
    def test_hook_file_is_executable(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm.os.system", return_value=0)
        _init_pre_commit_hook()
        hook_path = tmp_project / ".githooks" / "pre-commit"
        # Check if executable bit is set
        st_mode = os.stat(str(hook_path)).st_mode
        assert bool(st_mode & stat.S_IXUSR)

    def test_calls_git_config(self, tmp_project, mocker):
        mock_system = mocker.patch("mcp_decisions_llm.os.system", return_value=0)
        _init_pre_commit_hook()
        mock_system.assert_called_once_with("git config core.hooksPath .githooks")

    def test_idempotent_skips_file_creation(self, tmp_project, mocker):
        mock_system = mocker.patch("mcp_decisions_llm.os.system", return_value=0)
        _init_pre_commit_hook()
        hook_path = tmp_project / ".githooks" / "pre-commit"
        custom_content = "custom"
        hook_path.write_text(custom_content)
        mock_system.reset_mock()
        _init_pre_commit_hook()
        assert hook_path.read_text() == custom_content
        # git config is still called once per invocation
        mock_system.assert_called_once()

    def test_git_config_nonzero_prints_warning(self, tmp_project, mocker, capsys):
        mocker.patch("mcp_decisions_llm.os.system", return_value=1)
        _init_pre_commit_hook()
        captured = capsys.readouterr()
        assert "WARNING:" in captured.err

    def test_creates_githooks_dir(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm.os.system", return_value=0)
        _init_pre_commit_hook()
        assert (tmp_project / ".githooks").exists()


class TestInitProject:
    def test_creates_claude_md_when_absent(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm._init_github_actions_workflow")
        mocker.patch("mcp_decisions_llm._init_pre_commit_hook")
        init_project()
        assert (tmp_project / "CLAUDE.md").exists()

    def test_new_claude_md_starts_with_header(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm._init_github_actions_workflow")
        mocker.patch("mcp_decisions_llm._init_pre_commit_hook")
        init_project()
        content = (tmp_project / "CLAUDE.md").read_text()
        assert content.startswith("# Project CLAUDE.md")

    def test_claude_md_contains_protocol_text(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm._init_github_actions_workflow")
        mocker.patch("mcp_decisions_llm._init_pre_commit_hook")
        init_project()
        content = (tmp_project / "CLAUDE.md").read_text()
        assert "Engineering Conformance Protocol" in content

    def test_appends_to_existing_claude_md(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm._init_github_actions_workflow")
        mocker.patch("mcp_decisions_llm._init_pre_commit_hook")
        (tmp_project / "CLAUDE.md").write_text("# My Existing Header\n")
        init_project()
        content = (tmp_project / "CLAUDE.md").read_text()
        assert "# My Existing Header" in content
        assert "Engineering Conformance Protocol" in content

    def test_idempotent_no_duplicate_protocol(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm._init_github_actions_workflow")
        mocker.patch("mcp_decisions_llm._init_pre_commit_hook")
        init_project()
        init_project()
        content = (tmp_project / "CLAUDE.md").read_text()
        # Count occurrences of the protocol text
        assert content.count("Engineering Conformance Protocol") == 1

    def test_calls_workflow_init(self, tmp_project, mocker):
        mock_workflow = mocker.patch("mcp_decisions_llm._init_github_actions_workflow")
        mocker.patch("mcp_decisions_llm._init_pre_commit_hook")
        init_project()
        mock_workflow.assert_called_once()

    def test_calls_pre_commit_hook_init(self, tmp_project, mocker):
        mocker.patch("mcp_decisions_llm._init_github_actions_workflow")
        mock_hook = mocker.patch("mcp_decisions_llm._init_pre_commit_hook")
        init_project()
        mock_hook.assert_called_once()
