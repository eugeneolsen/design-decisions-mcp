#!/usr/bin/env python3
import os
import re
import sys
import yaml

DECISIONS_DIR = os.path.join(".continue", "decisions")
REQUIRED_FIELDS = ["id", "title", "description", "tags"]

def validate_file(file_path):
    if not file_path.endswith(".md"):
        return True

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for standard YAML boundary format markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            print(f"❌ ERROR: {file_path} is missing standard YAML front matter delimiters (---).")
            return False

        try:
            meta = yaml.safe_load(match.group(1))
        except Exception as e:
            print(f"❌ ERROR: {file_path} has malformed YAML syntax: {e}")
            return False

        if not meta:
            print(f"❌ ERROR: {file_path} contains an empty front matter block.")
            return False

        # Validate existence of mandatory processing fields
        for field in REQUIRED_FIELDS:
            if field not in meta or not str(meta[field]).strip():
                print(f"❌ ERROR: {file_path} is missing the mandatory '{field}' field in its front matter.")
                return False

        if not isinstance(meta["tags"], list) or len(meta["tags"]) == 0:
            print(f"❌ ERROR: {file_path} 'tags' property must be a non-empty YAML list layout.")
            return False

        print(f"✅ PASSED: {file_path} contains a valid JIT token index schema.")
        return True

    except Exception as e:
        print(f"❌ CRITICAL: Failed reading file {file_path}: {e}")
        return False

def main():
    files_to_check = sys.argv[1:]
    
    if not files_to_check and os.path.isdir(DECISIONS_DIR):
        files_to_check = [os.path.join(DECISIONS_DIR, f) for f in os.listdir(DECISIONS_DIR) if f.endswith(".md")]

    has_errors = False
    for file_path in files_to_check:
        if DECISIONS_DIR in file_path:
            if not validate_file(file_path):
                has_errors = True

    if has_errors:
        print("\n🚨 Architecture conformance validation failed. Fix the metadata syntax errors above before committing.")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
