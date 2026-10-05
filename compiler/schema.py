# ─── CGRF Header ───────────────────────────────────────────────
# File:        compiler/schema.py
# Stage:       07_BUILD
# SRS:         SRS-GUILD-BOOTSTRAP-001
# CAPS:        pending
# CK:          pending
# Dispatch:    user-authorized-bootstrap
# Seat:        BITS-CODEGEN
# Owner:       Citadel Nexus Inc.
# Created:     2026-10-05
# Depends:     none
# EnumType:    Service
# EnumEdges:   DEPENDS_ON SRS-GUILD-BOOTSTRAP-001
# DAG Node:    none
# Intent:      Validate guild contracts locally without granting runtime authority.
# ───────────────────────────────────────────────────────────────

"""Check the explicit JSON Schema subset used by the governance contracts."""

from __future__ import annotations

import re
from typing import Any

from compiler.yaml_subset import CitadelError


class SchemaError(CitadelError):
    """Report an invalid or unsupported schema definition."""


TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}
KEYWORDS = {
    "$schema", "$defs", "title", "description", "type", "properties", "required",
    "additionalProperties", "items", "enum", "const", "pattern", "minLength",
    "minItems", "maxItems", "uniqueItems", "minimum", "maximum",
}


def check_schema(schema: Any, path: str = "schema") -> None:
    """Reject malformed schemas and unsupported validation keywords."""
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: schema must be a mapping")
    if set(schema) - KEYWORDS:
        raise SchemaError(f"{path}: unsupported keywords: {sorted(set(schema) - KEYWORDS)}")
    if schema.get("type") not in TYPES:
        raise SchemaError(f"{path}: one supported type is required")
    for keyword in ("$schema", "title", "description", "pattern"):
        if keyword in schema and not isinstance(schema[keyword], str):
            raise SchemaError(f"{path}.{keyword}: expected string")
    for keyword in ("properties", "$defs"):
        if keyword in schema:
            if not isinstance(schema[keyword], dict):
                raise SchemaError(f"{path}.{keyword}: expected mapping")
            for key, child in schema[keyword].items():
                check_schema(child, f"{path}.{keyword}.{key}")
    if "items" in schema:
        check_schema(schema["items"], f"{path}.items")
    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list) or any(not isinstance(k, str) for k in required):
            raise SchemaError(f"{path}.required: expected string array")
        if len(set(required)) != len(required) or set(required) - set(schema.get("properties", {})):
            raise SchemaError(f"{path}.required: duplicate or undeclared properties")
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        raise SchemaError(f"{path}.enum: expected nonempty array")
    for keyword in ("additionalProperties", "uniqueItems"):
        if keyword in schema and not isinstance(schema[keyword], bool):
            raise SchemaError(f"{path}.{keyword}: expected boolean")
    for keyword in ("minLength", "minItems", "maxItems"):
        if keyword in schema and (type(schema[keyword]) is not int or schema[keyword] < 0):
            raise SchemaError(f"{path}.{keyword}: expected nonnegative integer")
    for keyword in ("minimum", "maximum"):
        if keyword in schema and type(schema[keyword]) not in (int, float):
            raise SchemaError(f"{path}.{keyword}: expected number")
    if "pattern" in schema:
        try:
            re.compile(schema["pattern"])
        except re.error as exc:
            raise SchemaError(f"{path}.pattern: invalid regular expression") from exc


def validate_value(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    """Return deterministic validation diagnostics for one schema instance."""
    kind = schema["type"]
    matches = {
        "object": isinstance(value, dict), "array": isinstance(value, list),
        "string": isinstance(value, str), "integer": type(value) is int,
        "number": type(value) in (int, float), "boolean": type(value) is bool,
        "null": value is None,
    }
    if not matches[kind]:
        return [f"{path}: expected {kind}"]
    errors: list[str] = []
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and not any(type(value) is type(v) and value == v for v in schema["enum"]):
        errors.append(f"{path}: value is outside enum")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required property missing")
        for key, child in value.items():
            if key in props:
                errors.extend(validate_value(child, props[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: unknown property")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            errors.append(f"{path}: invalid array length")
        if schema.get("uniqueItems") and any(item in value[:i] for i, item in enumerate(value)):
            errors.append(f"{path}: duplicate array items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(validate_value(item, schema["items"], f"{path}[{index}]"))
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is too short")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: string does not match pattern")
    elif type(value) in (int, float):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            errors.append(f"{path}: number outside bounds")
    return errors
