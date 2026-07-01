DECISION_RECORD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Unified Decision Record Schema (XDR)",
    "type": "object",
    "required": ["id", "type", "title", "date", "status", "context", "decision", "consequences"],
    "additionalProperties": False,
    "allOf": [
        {"if": {"properties": {"type": {"const": "architecture"}}}, "then": {"properties": {"id": {"pattern": "^ADR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "design"}}}, "then": {"properties": {"id": {"pattern": "^DDR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "operations"}}}, "then": {"properties": {"id": {"pattern": "^ODR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "security"}}}, "then": {"properties": {"id": {"pattern": "^SDR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "product"}}}, "then": {"properties": {"id": {"pattern": "^TDR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "process"}}}, "then": {"properties": {"id": {"pattern": "^PDR-[0-9]{4}$"}}}},
        {"if": {"properties": {"type": {"const": "functional"}}}, "then": {"properties": {"id": {"pattern": "^FDR-[0-9]{4}$"}, "consequences": {"required": ["acceptance_criteria"]}}}},
    ],
    "properties": {
        "id": {"type": "string", "description": "Unique identifier prefixed by domain type (e.g., ADR-0001, SDR-0022)"},
        "type": {
            "type": "string",
            "enum": ["architecture", "design", "operations", "security", "product", "process", "functional"],
            "description": "The specific domain category of the decision record.",
        },
        "title": {"type": "string", "minLength": 10, "description": "Clear, descriptive title of the decision."},
        "date": {"type": "string", "format": "date", "description": "The date the record was created or updated (YYYY-MM-DD)."},
        "status": {
            "type": "string",
            "enum": ["proposed", "accepted", "implemented", "rejected", "deprecated", "superseded"],
            "description": "The current lifecycle state of the decision.",
        },
        "supersedes": {"type": "string", "pattern": "^[A-Z]{3}-[0-9]{4}$", "description": "The ID of an earlier record that this new decision replaces."},
        "meta": {
            "type": "object",
            "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        },
        "context": {"type": "string", "minLength": 20, "description": "The background problem statement and technical forces driving this decision."},
        "decision": {
            "type": "object",
            "required": ["chosen_option", "justification"],
            "properties": {
                "chosen_option": {"type": "string"},
                "justification": {"type": "string"},
                "api_contract": {
                    "type": "object",
                    "description": "Optional HTTP endpoint or JSON schema contract.",
                },
                "state_transitions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["from", "event", "to"],
                        "additionalProperties": False,
                        "properties": {
                            "from": {"type": "string"},
                            "event": {"type": "string"},
                            "to": {"type": "string"},
                            "side_effects": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        },
        "consequences": {
            "type": "object",
            "required": [],
            "additionalProperties": False,
            "properties": {
                "enforced_constraints": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "description": "Explicit 'Do' or 'Do Not' constraint strings evaluated by the AI harness."},
                },
                "classified_consequences": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["impact", "description"],
                        "additionalProperties": False,
                        "properties": {
                            "impact": {"type": "string", "enum": ["good", "bad", "neutral"], "description": "The polarity of the consequence based on MADR industry conventions."},
                            "description": {"type": "string", "minLength": 5, "description": "The textual description of the consequence."},
                        },
                    },
                },
                "acceptance_criteria": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                    "description": "Given-When-Then behavioral expectations for functional specs.",
                },
            },
        },
        "implementation_tasks": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 5, "description": "A transient, actionable checklist item required to put this decision into effect."},
            "description": "Optional ephemeral tasks or migration steps required to execute this change.",
        },
    },
}
