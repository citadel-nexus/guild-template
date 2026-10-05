# ─── CGRF Header ───────────────────────────────────────────────
# File:        tests/test_materialize.py
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

"""Exercise generation, safe identity substitution and destination protection."""

from __future__ import annotations

import subprocess
import sys
from unittest import mock
import unittest

from compiler.materialize import MaterializeError, materialize
from compiler.validate import REQUIRED_FILES, validate_guild
from compiler.yaml_subset import load
from helpers import GuildFixture, ROOT, approve, edit


class MaterializeTests(GuildFixture):
    """Check the generated skeleton and failure cleanup behavior."""

    def test_generated_structure_and_identity(self) -> None:
        for relative in REQUIRED_FILES:
            self.assertTrue((self.guild / relative).is_file(), relative)
        guild = load(self.guild / "governance/guild.yaml")
        self.assertEqual((guild["guild_id"], guild["display_name"], guild["status"]), ("alpha", "Alpha Guild", "draft"))
        self.assertEqual(load(self.guild / "contracts/events/namespace.yaml")["canonical"], ["citadel.alpha.>"])
        self.assertEqual(load(self.guild / "service.datadog.yaml")["dd-service"], "alpha")
        self.assertEqual(validate_guild(self.guild, self.guild / "schemas").errors, [])
        for name in (".git", ".codex", "src", "node_modules", "__pycache__"):
            self.assertFalse((self.guild / name).exists())
        levels = load(self.guild / "governance/authority.yaml")["levels"]
        self.assertTrue(all(v["approval"] == "pending" and not v["capabilities"] for v in levels.values()))

    def test_existing_destination_is_untouched(self) -> None:
        sentinel = self.guild / "sentinel.txt"
        sentinel.write_text("keep")
        with self.assertRaises(MaterializeError):
            materialize(self.guild, "beta", "Beta", ROOT)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_invalid_identifier_and_name(self) -> None:
        for guild_id, name in (("../escape", "Name"), ("Bad_Name", "Name"), ("a--b", "Name"),
                               ("valid", ""), ("valid", "line\nbreak")):
            with self.subTest(guild_id=guild_id, name=name), self.assertRaises(MaterializeError):
                materialize(self.base / "new", guild_id, name, ROOT)
        self.assertFalse((self.base / "new").exists())

    def test_display_name_is_not_yaml_injection(self) -> None:
        name = 'Example: "Quoted" # & <Guild>'
        path = materialize(self.base / "quoted", "quoted", name, ROOT)
        self.assertEqual(load(path / "governance/guild.yaml")["display_name"], name)

    def test_missing_parent_and_nested_source_are_refused(self) -> None:
        for destination in (self.base / "missing" / "child", ROOT / "generated-test-guild"):
            with self.assertRaises(MaterializeError):
                materialize(destination, "beta", "Beta", ROOT)

    def test_dangling_destination_symlink_is_refused(self) -> None:
        destination = self.base / "dangling"
        destination.symlink_to(self.base / "nonexistent")
        with self.assertRaises(MaterializeError):
            materialize(destination, "beta", "Beta", ROOT)
        self.assertTrue(destination.is_symlink())

    def test_invalid_template_does_not_publish_or_leave_staging(self) -> None:
        (self.guild / "CONSTITUTION.md").unlink()
        with self.assertRaises(MaterializeError):
            materialize(self.base / "new", "new", "New", self.guild)
        self.assertFalse((self.base / "new").exists())
        self.assertEqual(list(self.base.glob(".guild-bootstrap-*")), [])

    def test_does_not_copy_ratified_grants(self) -> None:
        approve(self.guild)
        with self.assertRaises(MaterializeError):
            materialize(self.base / "new", "new", "New", self.guild)

    def test_does_not_copy_approved_levels_in_a_draft(self) -> None:
        edit(self.guild, "governance/authority.yaml", lambda d: d["levels"]["A1"].update(
            approval="approved", approved_by="human-operator"))
        with self.assertRaises(MaterializeError):
            materialize(self.base / "new", "new", "New", self.guild)

    def test_preserves_extra_roles_and_uses_trusted_compiler(self) -> None:
        relative = "roles/human/reviewer.yaml"
        path = self.guild / relative
        source = (self.guild / "roles/human/_template.yaml").read_text()
        path.write_text(source.replace("roles/human/_template.yaml", relative).replace('"human-operator"', '"human-reviewer"'))
        (self.guild / "compiler/validate.py").write_text("raise RuntimeError('untrusted compiler')\n")
        generated = materialize(self.base / "new", "new", "New", self.guild)
        self.assertTrue((generated / relative).is_file())
        self.assertEqual((generated / "compiler/validate.py").read_bytes(), (ROOT / "compiler/validate.py").read_bytes())
        self.assertEqual(validate_guild(generated).errors, [])

    def test_does_not_copy_existing_namespace_or_dependencies(self) -> None:
        edit(self.guild, "contracts/capabilities.yaml", lambda d: d.update(requires=[{
            "guild_id":"external", "capability_id":"service"}]))
        with self.assertRaises(MaterializeError):
            materialize(self.base / "new", "new", "New", self.guild)

    def test_copy_failure_cleans_only_new_destination(self) -> None:
        destination = self.base / "failed"
        with mock.patch("compiler.materialize.shutil.copytree", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(MaterializeError):
                materialize(destination, "failed", "Failed", ROOT)
        self.assertFalse(destination.exists())
        self.assertTrue(self.guild.is_dir())
        self.assertEqual(list(self.base.glob(".guild-bootstrap-*")), [])

    def test_generated_compiler_runs_independently(self) -> None:
        for filename in ("validate.py", "cross_guild_check.py"):
            proc = subprocess.run([sys.executable, str(self.guild / "compiler" / filename), str(self.guild)],
                                  cwd=self.base, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("PASS", proc.stdout)

    def test_materialize_cli_succeeds_then_refuses_overwrite(self) -> None:
        command = [sys.executable, str(ROOT / "compiler/materialize.py"), str(self.base / "via-cli"),
                   "--guild-id", "via-cli", "--name", "CLI Guild"]
        first = subprocess.run(command, cwd=self.base, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = subprocess.run(command, cwd=self.base, capture_output=True, text=True)
        self.assertEqual(second.returncode, 1)
        self.assertIn("refusing to overwrite", second.stderr)
        self.assertNotIn("Traceback", second.stderr)


if __name__ == "__main__":
    unittest.main()
