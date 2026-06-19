#!/usr/bin/env python3
import json
import os
import sys

import jsonschema
import yaml

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TYPE_DIRS = {"adr", "ddr", "sdr", "odr", "tdr", "pdr"}
SCHEMA_PATH = os.path.join("docs", "decision-record-schema.json")


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(file_path, schema):
    if not file_path.endswith(".yaml"):
        return True
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            print(f"❌ ERROR: {file_path} is empty or could not be parsed.")
            return False
        jsonschema.validate(instance=data, schema=schema)
        print(f"✅ PASSED: {file_path}")
        return True
    except jsonschema.ValidationError as e:
        print(f"❌ ERROR: {file_path} — {e.message}")
        return False
    except jsonschema.SchemaError as e:
        print(f"❌ SCHEMA ERROR: {e.message}")
        return False
    except Exception as e:
        print(f"❌ CRITICAL: {file_path} — {e}")
        return False


def collect_files():
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if os.path.basename(dirpath) in TYPE_DIRS:
            for filename in filenames:
                if filename.endswith(".yaml"):
                    yield os.path.join(dirpath, filename)


def main():
    try:
        schema = load_schema()
    except Exception as e:
        print(f"❌ CRITICAL: Could not load schema from {SCHEMA_PATH}: {e}")
        sys.exit(1)

    files_to_check = sys.argv[1:] if sys.argv[1:] else list(collect_files())

    if not files_to_check:
        print("No decision record files found.")
        sys.exit(0)

    has_errors = False
    for file_path in files_to_check:
        if not validate_file(file_path, schema):
            has_errors = True

    if has_errors:
        print("\n🚨 Validation failed. Fix the errors above before committing.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
