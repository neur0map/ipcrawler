"""
JSON schema validation for templates.
"""

import json
from typing import Dict, Any
from jsonschema import validate, ValidationError


class TemplateSchema:
    """Strict JSON schema for template validation."""
    
    SCHEMA = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_-]+$",
                "maxLength": 100,
                "minLength": 1
            },
            "tool": {
                "type": "string", 
                "pattern": "^[a-zA-Z0-9_/-]+$",
                "maxLength": 50,
                "minLength": 1
            },
            "args": {
                "type": "array",
                "items": {
                    "type": "string",
                    "maxLength": 1000,
                    "minLength": 1,
                    "pattern": "^[^;&|`$()<>]*$"  # No shell metacharacters
                },
                "maxItems": 50,
                "minItems": 0
            },
            "description": {
                "type": "string",
                "maxLength": 500
            },
            "author": {
                "type": "string",
                "maxLength": 100
            },
            "version": {
                "type": "string",
                "maxLength": 20
            },
            "tags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "maxLength": 50
                },
                "maxItems": 10
            },
            "dependencies": {
                "type": "array",
                "items": {
                    "type": "string",
                    "maxLength": 100
                },
                "maxItems": 10
            },
            "env": {
                "type": "object",
                "patternProperties": {
                    "^[A-Z_][A-Z0-9_]*$": {
                        "type": "string",
                        "maxLength": 1000
                    }
                },
                "additionalProperties": False,
                "maxProperties": 10
            },
            "wordlist": {
                "type": "string",
                "maxLength": 500,
                "pattern": "^[^;&|`$()<>]*$"
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300
            },
            "target_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["ip", "domain", "url", "file", "port"]
                },
                "maxItems": 5
            },
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high"]
            },
            "stealth": {
                "type": "boolean"
            },
            "parallel_safe": {
                "type": "boolean"
            },
            "preset": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_.-]+$",
                "maxLength": 100,
                "description": "Preset name in format 'tool.preset_name' or 'global_preset'"
            },
            "variables": {
                "type": "object",
                "patternProperties": {
                    "^[a-zA-Z0-9_]+$": {
                        "type": "string",
                        "maxLength": 500
                    }
                },
                "additionalProperties": False,
                "maxProperties": 10,
                "description": "Custom variables for template substitution"
            }
        },
        "required": ["name", "tool"],
        "additionalProperties": False,
        "anyOf": [
            {"required": ["args"]},
            {"required": ["preset"]}
        ]
    }
    
    @classmethod
    def validate_template(cls, template_data: Dict[str, Any]) -> bool:
        """Validate template against schema."""
        try:
            validate(instance=template_data, schema=cls.SCHEMA)
            return True
        except ValidationError:
            return False
    
    @classmethod
    def validate_template_strict(cls, template_data: Dict[str, Any]) -> None:
        """Validate template and raise exception on failure."""
        validate(instance=template_data, schema=cls.SCHEMA)
    
    @classmethod
    def get_schema_json(cls) -> str:
        """Get schema as JSON string."""
        return json.dumps(cls.SCHEMA, indent=2)