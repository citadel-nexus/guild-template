# ─── CGRF Header ───────────────────────────────────────────────
# File:        tests/test_schemas.py
# Stage:       08_TEST
# SRS:         SRS-GUILD-BOOTSTRAP-001
# CAPS:        pending
# CK:          pending
# Dispatch:    user-authorized-bootstrap
# Seat:        BITS-CODEGEN
# Owner:       Citadel Nexus Inc.
# Created:     2026-10-05
# Depends:     none
# EnumType:    Test
# EnumEdges:   DEPENDS_ON SRS-GUILD-BOOTSTRAP-001
# DAG Node:    none
# Intent:      Verify governance contracts with isolated known-good and known-bad fixtures.
# ───────────────────────────────────────────────────────────────

"""Exercise schema compilation and the supported YAML subset."""

from __future__ import annotations

import unittest

from compiler.schema import SchemaError, check_schema, validate_value
from compiler.validate import SECTIONS, check_envelope
from compiler.yaml_subset import ParseError, load, loads
from helpers import ROOT


class SchemaTests(unittest.TestCase):
    """Check all shipped schemas as executable contracts."""

    def test_schemas_are_valid_yaml_and_supported_schemas(self) -> None:
        paths = sorted((ROOT / "schemas").glob("*.schema.yaml"))
        self.assertEqual(len(paths), 7)
        for path in paths:
            with self.subTest(path=path.name):
                check_schema(load(path))
                self.assertEqual(check_envelope(path.read_text(), path.relative_to(ROOT).as_posix()), [])

    def test_constitution_has_exactly_fourteen_sections(self) -> None:
        schema = load(ROOT / "schemas/constitution.schema.yaml")
        self.assertEqual(tuple(schema["properties"]["constitution"]["required"]), SECTIONS)

    def test_invalid_schemas_fail_closed(self) -> None:
        cases = [None, {}, {"type": "imaginary"}, {"type": "string", "$ref": "x"},
                 {"type": "object", "properties": []}, {"type": "array", "items": False},
                 {"type": "object", "required": ["undeclared"]},
                 {"type": "object", "required": [True]}, {"type": "string", "enum": []},
                 {"type": "string", "pattern": "["}, {"type": "string", "minLength": -1},
                 {"type": "object", "additionalProperties": {}},
                 {"type": "number", "minimum": "zero"}]
        for schema in cases:
            with self.subTest(schema=schema), self.assertRaises(SchemaError):
                check_schema(schema)

    def test_scalar_constraints(self) -> None:
        cases = [(True, {"type":"integer"}), (False, {"type":"number"}),
                 ("", {"type":"string", "minLength":1}),
                 (3, {"type":"number", "maximum":2}),
                 (0, {"type":"number", "minimum":1}),
                 (True, {"type":"boolean", "enum":[1]}),
                 (1, {"type":"integer", "const":True}),
                 ("A10", {"type":"string", "pattern":"^A[1-9]$"}),
                 ([1,1], {"type":"array", "uniqueItems":True}),
                 ([], {"type":"array", "minItems":1}),
                 ([1,2], {"type":"array", "maxItems":1}),
                 ({"x":1}, {"type":"object", "additionalProperties":False})]
        for value, schema in cases:
            with self.subTest(value=value, schema=schema):
                self.assertTrue(validate_value(value, schema, "test"))


class ParserTests(unittest.TestCase):
    """Check accepted syntax and known ambiguity/failure cases."""

    def test_nested_yaml_and_list_mappings(self) -> None:
        self.assertEqual(loads('''rows:
  - name: first
    values: [1, true, null]
    nested:
      enabled: false
  - name: second
    values: []
empty: {}
'''), {"rows":[{"name":"first", "values":[1, True, None], "nested":{"enabled":False}},
                     {"name":"second", "values":[]}], "empty":{}})

    def test_strings_comments_and_scalars(self) -> None:
        doc = loads('''single: 'it''s # literal'
double: "text # literal: yes" # comment
plain: yes # retained as a string
date: 2026-10-05
scientific: 1e2
negative: -4
nothing: ~
apostrophe: don't infer authority # comment
''')
        self.assertEqual(doc, {"single":"it's # literal", "double":"text # literal: yes",
                               "plain":"yes", "date":"2026-10-05", "scientific":100.0,
                               "negative":-4, "nothing":None,
                               "apostrophe":"don't infer authority"})

    def test_malformed_or_unsupported_yaml_is_rejected(self) -> None:
        cases = ["", "# comment", "a: 1\na: 2", 'a: {"x":1,"x":2}', "a:\n b: 1",
                 "a:\n    b: 1", "a: 1\n  b: 2", "a: 1\n- 2", "\ta: 1", "---\na: 1",
                 "a: 1\n...", "a: &ref value", "a: *ref", "a: !tag value", "a: |\n  x",
                 "a: >\n  x", "a: [unquoted]", "a: {key: value}", 'a: "unterminated',
                 "a: 'unterminated", "a: 'bad'quote'", "a: bad: value", "a: 1e999",
                 'a: {"x": NaN}', "a:\n  <<: value", "? key\n: value", "%YAML 1.2"]
        for source in cases:
            with self.subTest(source=source), self.assertRaises(ParseError):
                loads(source)

    def test_resource_bounds(self) -> None:
        for source in ("a: " + "x" * 1_000_000, "a: " + "[" * 42 + "0" + "]" * 42,
                       "\n".join("  " * i + "a:" for i in range(43))):
            with self.assertRaises(ParseError):
                loads(source)

    def test_root_json_and_empty_values(self) -> None:
        self.assertEqual(loads('{"a":[1,2]}'), {"a":[1,2]})
        self.assertEqual(loads("a:\nb: []"), {"a":None,"b":[]})


if __name__ == "__main__":
    unittest.main()
