import pytest

from mcp_decisions_llm import get_all_records, list_architecture_decisions, fetch_architecture_decision


class TestGetAllRecords:
    def test_empty_directory_returns_empty_dict(self, tmp_project):
        assert get_all_records() == {}

    def test_yaml_in_adr_dir_is_discovered(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        records = get_all_records()
        assert "docs/ADR-0001" in records
        assert len(records) == 1

    def test_root_level_type_dir_key_format(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("adr/ADR-0001.yaml", minimal_valid_record)
        records = get_all_records()
        assert "./ADR-0001" in records

    def test_all_six_type_dirs_are_discovered(self, tmp_project, write_yaml, minimal_valid_record):
        for type_dir in ["adr", "ddr", "sdr", "odr", "tdr", "pdr"]:
            record = minimal_valid_record.copy()
            record["type"] = "architecture"
            record["id"] = f"{type_dir.upper()}-0001"
            write_yaml(f"{type_dir}/{record['id']}.yaml", record)
        records = get_all_records()
        assert len(records) == 6

    def test_non_type_dir_is_ignored(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("decisions/ADR-0001.yaml", minimal_valid_record)
        assert get_all_records() == {}

    def test_hidden_directory_is_skipped(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml(".hidden/adr/ADR-0001.yaml", minimal_valid_record)
        assert get_all_records() == {}

    def test_non_yaml_file_is_ignored(self, tmp_project, write_yaml, minimal_valid_record):
        (tmp_project / "adr").mkdir(parents=True, exist_ok=True)
        (tmp_project / "adr" / "ADR-0001.json").write_text('{"id": "ADR-0001"}')
        (tmp_project / "adr" / "README.md").write_text("# ADR")
        assert get_all_records() == {}

    def test_empty_yaml_file_is_skipped(self, tmp_project, write_yaml):
        (tmp_project / "adr").mkdir(parents=True, exist_ok=True)
        (tmp_project / "adr" / "ADR-0001.yaml").write_text("")
        assert get_all_records() == {}

    def test_yaml_without_id_is_skipped(self, tmp_project, write_yaml, minimal_valid_record):
        record = minimal_valid_record.copy()
        del record["id"]
        write_yaml("adr/ADR-0001.yaml", record)
        assert get_all_records() == {}

    def test_yaml_that_is_a_list_is_skipped(self, tmp_project, write_yaml):
        (tmp_project / "adr").mkdir(parents=True, exist_ok=True)
        (tmp_project / "adr" / "ADR-0001.yaml").write_text("- item1\n- item2")
        assert get_all_records() == {}

    def test_record_data_fields_populated(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        records = get_all_records()
        entry = records["docs/ADR-0001"]
        assert entry["type"] == "architecture"
        assert entry["title"] == "Use something for something important"
        assert "We needed a way" in entry["context"]
        assert entry["tags"] == []
        assert "id" in entry["raw"]

    def test_id_is_uppercased(self, tmp_project, write_yaml, minimal_valid_record):
        record = minimal_valid_record.copy()
        record["id"] = "adr-0001"
        write_yaml("adr/test.yaml", record)
        records = get_all_records()
        assert "./ADR-0001" in records

    def test_missing_optional_fields_use_defaults(self, tmp_project, write_yaml):
        record = {"id": "ADR-0001"}
        write_yaml("adr/ADR-0001.yaml", record)
        records = get_all_records()
        entry = records["./ADR-0001"]
        assert entry["title"] == "Untitled Decision"
        assert entry["tags"] == []
        assert entry["context"] == ""

    def test_deeply_nested_type_dir(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("services/billing/adr/ADR-0001.yaml", minimal_valid_record)
        records = get_all_records()
        assert "services/billing/ADR-0001" in records

    def test_multiple_yamls_in_same_type_dir(self, tmp_project, write_yaml, minimal_valid_record):
        for i in range(1, 3):
            record = minimal_valid_record.copy()
            record["id"] = f"ADR-000{i}"
            write_yaml(f"adr/ADR-000{i}.yaml", record)
        records = get_all_records()
        assert len(records) == 2


class TestListArchitectureDecisions:
    def test_no_records_returns_help_message(self, tmp_project):
        result = list_architecture_decisions()
        assert "No decision records found." in result

    def test_returns_registry_header(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        result = list_architecture_decisions()
        assert "=== ARCHITECTURAL REGISTRY ===" in result

    def test_output_contains_scoped_id(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        result = list_architecture_decisions()
        assert "ID: docs/ADR-0001" in result

    def test_output_contains_type_and_title(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        result = list_architecture_decisions()
        assert "Type: architecture" in result
        assert "Title: Use something for something important" in result

    def test_context_truncated_at_120_chars(self, tmp_project, write_yaml, minimal_valid_record):
        record = minimal_valid_record.copy()
        record["context"] = "x" * 200
        write_yaml("docs/adr/ADR-0001.yaml", record)
        result = list_architecture_decisions()
        assert "..." in result
        # Find the context line and verify it's not too long
        for line in result.split("\n"):
            if line.startswith("Context:"):
                assert len(line) <= 135  # 120 chars + "Context: " + "..."

    def test_context_not_truncated_when_short(self, tmp_project, write_yaml, minimal_valid_record):
        record = minimal_valid_record.copy()
        record["context"] = "x" * 50
        write_yaml("docs/adr/ADR-0001.yaml", record)
        result = list_architecture_decisions()
        # Should have context line without ellipsis for short context
        assert "Context: " + "x" * 50 in result

    def test_records_sorted_alphabetically(self, tmp_project, write_yaml, minimal_valid_record):
        record_b = minimal_valid_record.copy()
        record_b["id"] = "ADR-0002"
        write_yaml("adr/ADR-0001.yaml", minimal_valid_record)
        write_yaml("adr/ADR-0002.yaml", record_b)
        result = list_architecture_decisions()
        pos_0001 = result.find("./ADR-0001")
        pos_0002 = result.find("./ADR-0002")
        assert pos_0001 < pos_0002

    def test_tags_joined_with_comma(self, tmp_project, write_yaml, minimal_valid_record):
        record = minimal_valid_record.copy()
        record["meta"] = {"tags": ["alpha", "beta"]}
        write_yaml("docs/adr/ADR-0001.yaml", record)
        result = list_architecture_decisions()
        assert "Tags: alpha, beta" in result

    def test_tags_empty_when_no_meta(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        result = list_architecture_decisions()
        assert "Tags: \n" in result or result.endswith("Tags: ")


class TestFetchArchitectureDecision:
    def test_fetches_existing_record(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        result = fetch_architecture_decision("docs/ADR-0001")
        assert "=== CONFORMANCE GUARDRAIL: docs/ADR-0001 ===" in result

    def test_returns_error_for_missing_id(self, tmp_project):
        result = fetch_architecture_decision("docs/ADR-9999")
        assert "Error:" in result
        assert "not found" in result

    def test_strips_whitespace_from_id(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        result = fetch_architecture_decision("  docs/ADR-0001  ")
        assert "CONFORMANCE GUARDRAIL" in result

    def test_response_contains_yaml_dump(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        result = fetch_architecture_decision("docs/ADR-0001")
        assert "Full Record:" in result
        assert "architecture" in result  # type should be in YAML

    def test_response_includes_title_line(self, tmp_project, write_yaml, minimal_valid_record):
        write_yaml("docs/adr/ADR-0001.yaml", minimal_valid_record)
        result = fetch_architecture_decision("docs/ADR-0001")
        assert "Title: Use something for something important" in result
