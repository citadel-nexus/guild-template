# ─── CGRF Header ───────────────────────────────────────────────
# File:        compiler/yaml_subset.py
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

"""Parse the documented, deliberately small governance YAML subset."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


class CitadelError(Exception):
    """Represent a governance compiler error."""


class ParseError(CitadelError):
    """Report unsupported or malformed governance YAML."""


MAX_BYTES = 1_000_000
MAX_DEPTH = 40
KEY = re.compile(r"^[A-Za-z_$][A-Za-z0-9_.$/-]*$")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ParseError(f"duplicate key: {key}")
        result[key] = value
    return result


def _comment(line: str) -> str:
    quote = ""
    escaped = False
    index = 0
    while index < len(line):
        char = line[index]
        if escaped:
            escaped = False
        elif quote == '"' and char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                if quote == "'" and line[index:index + 2] == "''":
                    index += 2
                    continue
                quote = ""
        elif char in "\"'" and (not line[:index].strip() or line[:index].rstrip().endswith((":", "[", "{", ",", "-"))):
            quote = char
        elif char == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
        index += 1
    return line.rstrip()


def _scalar(value: str) -> Any:
    if value.startswith(('"', "[", "{")):
        try:
            parsed = json.loads(value, object_pairs_hook=_pairs)
        except (ValueError, RecursionError) as exc:
            raise ParseError(f"invalid JSON-style scalar/container: {value[:80]}") from exc
        return parsed
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise ParseError("unterminated single-quoted scalar")
        inner = value[1:-1]
        if "'" in inner.replace("''", ""):
            raise ParseError("single quotes must be doubled")
        return inner.replace("''", "'")
    if value.startswith(("&", "*", "!", "|", ">", "@", "`", "%")):
        raise ParseError("anchors, aliases, tags and block scalars are unsupported; quote strings")
    if ": " in value or value.endswith(":") or value.startswith("- "):
        raise ParseError("ambiguous plain scalar; quote this value")
    if value in {"true", "false", "null", "~"}:
        return {"true": True, "false": False, "null": None, "~": None}[value]
    if re.fullmatch(r"-?(0|[1-9][0-9]*)", value):
        try:
            return int(value)
        except ValueError as exc:
            raise ParseError("integer is too large") from exc
    if re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?", value):
        return float(value)
    return value


def _bounded(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ParseError("maximum nesting depth exceeded")
    if isinstance(value, float) and not math.isfinite(value):
        raise ParseError("non-finite numbers are unsupported")
    if isinstance(value, dict):
        for item in value.values():
            _bounded(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _bounded(item, depth + 1)


def loads(source: str) -> Any:
    """Parse mappings, sequences and scalars without implicit YAML coercion."""
    if len(source.encode("utf-8")) > MAX_BYTES:
        raise ParseError("document exceeds size limit")
    rows: list[tuple[int, str, int]] = []
    for number, line in enumerate(source.splitlines(), 1):
        if "\t" in line:
            raise ParseError(f"line {number}: tabs are unsupported")
        content = _comment(line)
        if not content.strip():
            continue
        indent = len(content) - len(content.lstrip(" "))
        if indent % 2:
            raise ParseError(f"line {number}: use two-space indentation")
        value = content[indent:]
        if value in {"---", "..."} or value.startswith("%"):
            raise ParseError(f"line {number}: directives and multiple documents are unsupported")
        rows.append((indent, value, number))
    if not rows:
        raise ParseError("empty document")

    def pair(text: str, number: int) -> tuple[str, str]:
        match = re.fullmatch(r"([^:]+):(?: +(.*))?", text)
        if not match or not KEY.fullmatch(match[1]):
            raise ParseError(f"line {number}: expected a plain mapping key")
        return match[1], match[2] or ""

    def block(index: int, indent: int, depth: int) -> tuple[Any, int]:
        if depth > MAX_DEPTH:
            raise ParseError("maximum nesting depth exceeded")
        if rows[index][0] != indent:
            raise ParseError(f"line {rows[index][2]}: unexpected indentation")
        sequence = rows[index][1] == "-" or rows[index][1].startswith("- ")
        mapping: dict[str, Any] = {}
        items: list[Any] = []
        while index < len(rows) and rows[index][0] >= indent:
            current_indent, text, number = rows[index]
            if current_indent != indent:
                raise ParseError(f"line {number}: unexpected indentation")
            is_item = text == "-" or text.startswith("- ")
            if sequence != is_item:
                raise ParseError(f"line {number}: mixed sequence and mapping")
            if sequence:
                raw = text[1:].strip()
                if re.match(r"^[A-Za-z_$][A-Za-z0-9_.$/-]*:(?: |$)", raw):
                    rows[index] = (indent + 2, raw, number)
                    value, index = block(index, indent + 2, depth + 1)
                    items.append(value)
                    continue
                key = ""
            else:
                key, raw = pair(text, number)
                if key in mapping:
                    raise ParseError(f"line {number}: duplicate key: {key}")
            index += 1
            if raw:
                value = _scalar(raw)
            elif index < len(rows) and rows[index][0] > indent:
                value, index = block(index, indent + 2, depth + 1)
            else:
                value = None
            if sequence:
                items.append(value)
            else:
                mapping[key] = value
        return (items if sequence else mapping), index

    # JSON is a supported flow representation of YAML, including root values.
    if len(rows) == 1 and rows[0][0] == 0 and rows[0][1].startswith(("{", "[")):
        result = _scalar(rows[0][1])
    else:
        result, end = block(0, 0, 0)
        if end != len(rows):
            raise ParseError("unconsumed input")
    _bounded(result)
    return result


def load(path: Path) -> Any:
    """Read a bounded UTF-8 governance YAML document."""
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ParseError("document exceeds size limit")
        return loads(data.decode("utf-8"))
    except (OSError, UnicodeError) as exc:
        raise ParseError(f"cannot read {path}: {exc}") from exc
