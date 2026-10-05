# ─── CGRF Header ───────────────────────────────────────────────
# File:        tests/test_compiler.py
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

"""Verify that malformed guild contracts fail local validation."""

from __future__ import annotations

import subprocess
import sys
import unittest

from compiler.validate import REQUIRED_FILES, check_envelope, validate_guild
from helpers import GuildFixture, ROOT, activate_delegation, approve, edit, provide


class CompilerTests(GuildFixture):
    """Exercise structural validation, references and conservative authority."""

    def assert_failure(self, message: str) -> None:
        """Require a diagnostic containing the expected category."""
        errors = validate_guild(self.guild).errors
        self.assertTrue(any(message in e for e in errors), errors)

    def test_template_and_materialized_guild_are_valid(self) -> None:
        self.assertEqual(validate_guild(ROOT).errors, [])
        self.assertEqual(validate_guild(self.guild).errors, [])

    def test_each_required_file_is_enforced(self) -> None:
        for relative in REQUIRED_FILES:
            with self.subTest(relative=relative):
                path = self.guild / relative
                saved = path.read_bytes()
                path.unlink()
                self.assert_failure("required file missing")
                path.write_bytes(saved)

    def test_unknown_fields_and_authority_levels(self) -> None:
        edit(self.guild, "roles/agents/_template.yaml", lambda d: d.update(authority_level="A10", surprise=True))
        self.assert_failure("outside enum")
        self.assert_failure("unknown property")

    def test_invalid_yaml_is_a_diagnostic(self) -> None:
        path = self.guild / "governance/guild.yaml"
        path.write_text(path.read_text() + "bad: &anchor value\n")
        self.assert_failure("unsupported")

    def test_missing_schema_is_a_diagnostic(self) -> None:
        (self.guild / "schemas/roles.schema.yaml").unlink()
        self.assertTrue(validate_guild(self.guild, self.guild / "schemas").errors)

    def test_envelope_fields_and_srs(self) -> None:
        path = self.guild / "governance/guild.yaml"
        source = path.read_text()
        for old, new, message in [("# File:        governance/guild.yaml", "# File:        wrong.yaml", "CGRF File"),
                                  ("# Owner:       Citadel Nexus Inc.", "# Owner:       Wrong Owner", "legal owner"),
                                  ("# Created:     2026-10-05", "# Created:     invalid", "creation date"),
                                  ("SRS-GUILD-BOOTSTRAP-001", "SRS-UNKNOWN-001", "not registered"),
                                  ("# Stage:       06_PLAN", "# Stage:       invalid", "invalid CGRF stage")]:
            with self.subTest(message=message):
                path.write_text(source.replace(old, new))
                self.assert_failure(message)
        path.write_text(source)
        self.assertTrue(check_envelope("identity: x", "governance/guild.yaml"))

    def test_symlinks_are_not_followed(self) -> None:
        path = self.guild / "operations/SLO.yaml"
        path.unlink()
        path.symlink_to(ROOT / "operations/SLO.yaml")
        self.assert_failure("symlinks are not allowed")

    def test_constitution_sections_are_required(self) -> None:
        path = self.guild / "CONSTITUTION.md"
        path.write_text(path.read_text().replace("## Succession", "## Unrelated"))
        self.assert_failure("14 constitutional sections")

    def test_ratification_cannot_leave_prompts(self) -> None:
        edit(self.guild, "governance/guild.yaml", lambda d: d.update(status="ratified"))
        self.assert_failure("unanswered prompts")

    def test_pending_authority_cannot_grant_capabilities(self) -> None:
        edit(self.guild, "roles/agents/_template.yaml", lambda d: d.update(capabilities=["execute"]))
        self.assert_failure("approved authority")
        self.assert_failure("capabilities exceed")

    def test_no_parent_inheritance(self) -> None:
        edit(self.guild, "governance/authority.yaml", lambda d: d.update(inherit_parent_authority=True))
        self.assert_failure("expected constant")

    def test_approved_authority_requires_human_approver(self) -> None:
        approve(self.guild)
        edit(self.guild, "governance/authority.yaml", lambda d: d["levels"]["A1"].update(approved_by="agent-worker"))
        self.assert_failure("approver must be a human")

    def test_escalation_and_mandate_references(self) -> None:
        edit(self.guild, "governance/escalation.yaml", lambda d: d.update(default_route="missing"))
        edit(self.guild, "governance/mandates.yaml", lambda d: d["mandates"][0].update(cadence="missing", slos=["missing"]))
        self.assert_failure("escalation.default_route: unknown reference")
        self.assert_failure("mandate.governance-review.cadence: unknown reference")
        self.assert_failure("mandate.governance-review.slos: unknown reference")

    def test_extra_role_files_are_validated_and_ids_unique(self) -> None:
        path = self.guild / "roles/agents/another.yaml"
        source = (self.guild / "roles/agents/_template.yaml").read_text()
        path.write_text(source.replace("roles/agents/_template.yaml", "roles/agents/another.yaml"))
        self.assert_failure("duplicate role_id")

    def test_role_directory_kind_is_enforced(self) -> None:
        edit(self.guild, "roles/agents/_template.yaml", lambda d: d.update(kind="human"))
        self.assert_failure("role kind does not match")

    def test_slo_bounds(self) -> None:
        edit(self.guild, "operations/SLO.yaml", lambda d: d["slos"][0].update(target=1.1))
        self.assert_failure("outside bounds")

    def test_service_identity_and_namespace_owner(self) -> None:
        edit(self.guild, "service.datadog.yaml", lambda d: d.update({"dd-service":"other"}))
        edit(self.guild, "contracts/events/namespace.yaml", lambda d: d.update(owner="other"))
        self.assert_failure("dd-service must match")
        self.assert_failure("events.owner")

    def test_alias_target_sunset_and_local_overlap(self) -> None:
        edit(self.guild, "contracts/events/namespace.yaml", lambda d: d.update(deprecated_aliases=[{
            "alias":"citadel.alpha.updated", "canonical":"citadel.missing.>",
            "reason":"Test migration", "sunset":"2026-02-30",
        }]))
        self.assert_failure("unknown canonical target")
        self.assert_failure("invalid sunset date")
        self.assert_failure("overlapping namespace claims")

    def test_valid_service_contract_requires_domain_grant(self) -> None:
        provide(self.guild, "beta")
        self.assertEqual(validate_guild(self.guild).errors, [])
        edit(self.guild, "governance/hierarchy.yaml", lambda d: d.update(domain_authority=[]))
        self.assert_failure("missing explicit domain grant")

    def test_valid_delegation_and_expiry(self) -> None:
        activate_delegation(self.guild)
        self.assertEqual(validate_guild(self.guild).errors, [])
        edit(self.guild, "contracts/delegation/_template.yaml", lambda d: d.update(expires_at="2000-01-01T00:00:00Z"))
        self.assert_failure("future timezone-aware expiry")

    def test_delegation_cannot_exceed_role_or_scope(self) -> None:
        activate_delegation(self.guild)
        edit(self.guild, "roles/agents/_template.yaml", lambda d: d.update(capabilities=[]))
        edit(self.guild, "contracts/delegation/_template.yaml", lambda d: d.update(scope=["unowned.domain"]))
        self.assert_failure("exceeds to_role authority")
        self.assert_failure("scope lacks an explicit domain grant")

    def test_cli_failure_has_no_traceback(self) -> None:
        (self.guild / "governance/guild.yaml").unlink()
        proc = subprocess.run([sys.executable, str(ROOT / "compiler/validate.py"), str(self.guild)],
                              cwd=self.base, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
