import pytest
import yaml

from mcp_decisions_llm import _validate_single_file, validate_decisions, DECISION_RECORD_SCHEMA


class TestValidateSingleFile:
    def test_non_yaml_file_returns_true(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Read me")
        assert _validate_single_file(str(readme), DECISION_RECORD_SCHEMA) is True

    def test_valid_yaml_returns_true(self, tmp_path):
        adr = tmp_path / "ADR-0001.yaml"
        adr.write_text(
            yaml.dump(
                {
                    "id": "ADR-0001",
                    "type": "architecture",
                    "title": "Use PostgreSQL",
                    "date": "2026-01-01",
                    "status": "accepted",
                    "context": "We need a relational database.",
                    "decision": {"chosen_option": "PostgreSQL", "justification": "Mature and open source."},
                    "consequences": {},
                }
            )
        )
        assert _validate_single_file(str(adr), DECISION_RECORD_SCHEMA) is True

    def test_empty_yaml_returns_false(self, tmp_path, capsys):
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        assert _validate_single_file(str(empty), DECISION_RECORD_SCHEMA) is False
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    def test_missing_required_field_returns_false(self, tmp_path, capsys):
        adr = tmp_path / "ADR-0001.yaml"
        adr.write_text(
            yaml.dump(
                {
                    "id": "ADR-0001",
                    "type": "architecture",
                    # missing title
                    "date": "2026-01-01",
                    "status": "accepted",
                    "context": "We need something.",
                    "decision": {"chosen_option": "X", "justification": "Good."},
                    "consequences": {},
                }
            )
        )
        assert _validate_single_file(str(adr), DECISION_RECORD_SCHEMA) is False
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    def test_additional_property_returns_false(self, tmp_path, capsys):
        adr = tmp_path / "ADR-0001.yaml"
        adr.write_text(
            yaml.dump(
                {
                    "id": "ADR-0001",
                    "type": "architecture",
                    "title": "Use something",
                    "date": "2026-01-01",
                    "status": "accepted",
                    "context": "We need something.",
                    "decision": {"chosen_option": "X", "justification": "Good."},
                    "consequences": {},
                    "extra_field": "should not be here",
                }
            )
        )
        assert _validate_single_file(str(adr), DECISION_RECORD_SCHEMA) is False

    def test_invalid_id_pattern_returns_false(self, tmp_path, capsys):
        adr = tmp_path / "ADR-0001.yaml"
        adr.write_text(
            yaml.dump(
                {
                    "id": "ADR-999",  # wrong digit count
                    "type": "architecture",
                    "title": "Use something",
                    "date": "2026-01-01",
                    "status": "accepted",
                    "context": "We need something.",
                    "decision": {"chosen_option": "X", "justification": "Good."},
                    "consequences": {},
                }
            )
        )
        assert _validate_single_file(str(adr), DECISION_RECORD_SCHEMA) is False

    def test_nonexistent_file_returns_false(self):
        assert _validate_single_file("/nonexistent/path/file.yaml", DECISION_RECORD_SCHEMA) is False

    def test_prints_passed_on_success(self, tmp_path, capsys):
        adr = tmp_path / "ADR-0001.yaml"
        adr.write_text(
            yaml.dump(
                {
                    "id": "ADR-0001",
                    "type": "architecture",
                    "title": "Use something",
                    "date": "2026-01-01",
                    "status": "accepted",
                    "context": "We need a relational database for this application.",
                    "decision": {"chosen_option": "X", "justification": "Good."},
                    "consequences": {},
                }
            )
        )
        _validate_single_file(str(adr), DECISION_RECORD_SCHEMA)
        captured = capsys.readouterr()
        assert "PASSED:" in captured.out

    def test_prints_error_on_validation_failure(self, tmp_path, capsys):
        adr = tmp_path / "ADR-0001.yaml"
        adr.write_text(yaml.dump({"id": "ADR-0001"}))
        _validate_single_file(str(adr), DECISION_RECORD_SCHEMA)
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out


class TestValidateDecisions:
    def test_no_files_found_returns_true(self, tmp_project):
        assert validate_decisions() is True

    def test_all_valid_files_returns_true(self, tmp_project, write_yaml, minimal_valid_record):
        for i in range(1, 3):
            record = minimal_valid_record.copy()
            record["id"] = f"ADR-000{i}"
            write_yaml(f"adr/ADR-000{i}.yaml", record)
        assert validate_decisions() is True

    def test_one_invalid_file_returns_false(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("adr/valid.yaml", minimal_valid_record)
        write_yaml("adr/invalid.yaml", {"id": "ADR-0002"})  # missing required fields
        assert validate_decisions() is False

    def test_explicit_files_list_valid_returns_true(self, tmp_project, tmp_path, minimal_valid_record):
        valid_file = tmp_path / "valid.yaml"
        valid_file.write_text(yaml.dump(minimal_valid_record))
        assert validate_decisions(files=[str(valid_file)]) is True

    def test_explicit_files_list_invalid_returns_false(self, tmp_project, tmp_path):
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text(yaml.dump({"id": "ADR-0001"}))
        assert validate_decisions(files=[str(invalid_file)]) is False

    def test_empty_explicit_files_list_triggers_walk(self, tmp_project):
        # empty list is falsy, falls to walk path; empty dir returns True
        assert validate_decisions(files=[]) is True

    def test_hidden_dirs_skipped_in_walk(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml(".venv/adr/ADR-0001.yaml", minimal_valid_record)
        assert validate_decisions() is True

    def test_non_type_dir_skipped_in_walk(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("decisions/ADR-0001.yaml", minimal_valid_record)
        assert validate_decisions() is True

    def test_prints_validation_failed_on_error(self, tmp_project, write_yaml, capsys):
        write_yaml("adr/invalid.yaml", {"id": "ADR-0001"})
        validate_decisions()
        captured = capsys.readouterr()
        assert "Validation failed" in captured.out
