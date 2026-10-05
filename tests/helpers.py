# ─── CGRF Header ───────────────────────────────────────────────
# File:        tests/helpers.py
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

"""Build isolated governance fixtures without changing repository templates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from typing import Any, Callable
import unittest

from compiler.materialize import materialize
from compiler.yaml_subset import load


ROOT = Path(__file__).resolve().parents[1]


def edit(root: Path, relative: str, change: Callable[[Any], None]) -> None:
    """Apply a fixture mutation while preserving its envelope."""
    path = root / relative
    doc = load(path)
    change(doc)
    envelope = path.read_text().split("\n\n", 1)[0]
    path.write_text(envelope + "\n\n" + json.dumps(doc) + "\n")


def ratify(root: Path) -> None:
    """Mark an isolated test fixture as ratified with completed prompts."""
    def change(doc: dict[str, Any]) -> None:
        doc["status"] = "ratified"
        doc["constitution"] = {key: f"Test decision for {key}." for key in doc["constitution"]}
    edit(root, "governance/guild.yaml", change)
    path = root / "CONSTITUTION.md"
    path.write_text(path.read_text().replace("PROMPT:", "Test decision:"))


def approve(root: Path, capabilities: list[str] | None = None, domain: str | None = None) -> None:
    """Create explicit authority and domain grants for a positive test fixture."""
    caps = capabilities or ["execute"]
    guild_id = load(root / "governance/guild.yaml")["guild_id"]
    ratify(root)
    edit(root, "governance/authority.yaml", lambda d: d["levels"]["A1"].update(
        capabilities=caps, approval="approved", approved_by="human-operator"))
    for path in ("roles/human/_template.yaml", "roles/agents/_template.yaml"):
        edit(root, path, lambda d: d.update(capabilities=caps))
    edit(root, "governance/hierarchy.yaml", lambda d: d.update(domain_authority=[{
        "domain": domain or f"{guild_id}.operations", "owner": guild_id,
        "authority_level": "A1", "capabilities": caps, "exclusive": True,
    }]))


def provide(root: Path, consumer: str, capability: str = "execute") -> None:
    """Add a service contract consistent with the fixture's domain authority."""
    guild_id = load(root / "governance/guild.yaml")["guild_id"]
    approve(root, [capability])
    edit(root, "contracts/capabilities.yaml", lambda d: d.update(provides=[{
        "id": capability, "provider": guild_id, "consumers": [consumer],
        "domain": f"{guild_id}.operations", "authority_level": "A1",
        "input_schema": "contracts/input.schema.json", "output_schema": "contracts/output.schema.json",
        "slo_ref": "governance-validity", "verification": ["python -m compiler.validate ."],
    }]))


def activate_delegation(root: Path) -> None:
    """Create a scoped, expiring delegation fixture."""
    guild_id = load(root / "governance/guild.yaml")["guild_id"]
    approve(root)
    expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    edit(root, "contracts/delegation/_template.yaml", lambda d: d.update(
        status="active", capabilities=["execute"], scope=[f"{guild_id}.operations"],
        expires_at=expires, approved_by="human-operator"))


class GuildFixture(unittest.TestCase):
    """Allocate a fresh materialized guild for each mutation test."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.guild = materialize(self.base / "alpha", "alpha", "Alpha Guild", ROOT)

    def second(self, guild_id: str = "beta") -> Path:
        """Create another isolated guild in this test's temporary directory."""
        return materialize(self.base / guild_id, guild_id, f"{guild_id.title()} Guild", ROOT)
