import sys

import pytest

from mcp_decisions_llm import main


class TestMainDispatch:
    def test_init_subcommand_calls_init_project(self, mocker, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmd", "init"])
        mock_init = mocker.patch("mcp_decisions_llm.init_project")
        main()
        mock_init.assert_called_once()

    def test_validate_subcommand_passes_exits_0(self, mocker, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmd", "validate"])
        mocker.patch("mcp_decisions_llm.validate_decisions", return_value=True)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_validate_subcommand_fails_exits_1(self, mocker, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmd", "validate"])
        mocker.patch("mcp_decisions_llm.validate_decisions", return_value=False)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_validate_passes_yaml_file_args(self, mocker, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmd", "validate", "foo.yaml", "bar.yaml"])
        mock_validate = mocker.patch("mcp_decisions_llm.validate_decisions", return_value=True)
        with pytest.raises(SystemExit):
            main()
        mock_validate.assert_called_once_with(files=["foo.yaml", "bar.yaml"])

    def test_validate_ignores_non_yaml_args(self, mocker, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmd", "validate", "README.md"])
        mock_validate = mocker.patch("mcp_decisions_llm.validate_decisions", return_value=True)
        with pytest.raises(SystemExit):
            main()
        mock_validate.assert_called_once_with(files=None)

    def test_default_runs_mcp_server(self, mocker, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmd"])
        mock_run = mocker.patch("mcp_decisions_llm.mcp.run")
        main()
        mock_run.assert_called_once_with(transport="stdio")

    def test_default_does_not_exit(self, mocker, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cmd"])
        mocker.patch("mcp_decisions_llm.mcp.run")
        # Should not raise SystemExit
        main()
