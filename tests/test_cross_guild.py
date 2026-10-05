# ─── CGRF Header ───────────────────────────────────────────────
# File:        tests/test_cross_guild.py
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

"""Exercise multi-guild ownership and relationship conflicts."""

from __future__ import annotations

import unittest

from compiler.cross_guild_check import check_guilds
from compiler.graphs import cycle_nodes, subjects_overlap
from helpers import GuildFixture, approve, edit, provide


class CrossGuildTests(GuildFixture):
    """Check conflicts with individually valid guild fixtures."""

    def test_independent_guilds_pass(self) -> None:
        self.assertEqual(check_guilds([self.guild, self.second()]), [])

    def test_duplicate_identity_and_empty_input(self) -> None:
        self.assertIn("duplicate guild_id", " ".join(check_guilds([self.guild, self.guild])))
        self.assertTrue(check_guilds([]))

    def test_namespace_collision(self) -> None:
        beta = self.second()
        edit(beta, "contracts/events/namespace.yaml", lambda d: d.update(canonical=["citadel.alpha.updated"]))
        self.assertIn("namespace collision", " ".join(check_guilds([self.guild, beta])))

    def test_deprecated_alias_reserves_namespace(self) -> None:
        beta = self.second()
        edit(beta, "contracts/events/namespace.yaml", lambda d: d.update(deprecated_aliases=[{
            "alias":"citadel.alpha.*", "canonical":"citadel.beta.>",
            "reason":"Migration fixture", "sunset":"2030-01-01",
        }]))
        self.assertIn("namespace collision", " ".join(check_guilds([self.guild, beta])))

    def test_acknowledged_hierarchy_does_not_grant_authority(self) -> None:
        beta = self.second()
        for root in (self.guild, beta):
            edit(root, "governance/hierarchy.yaml", lambda d: d.update(
                organizational_hierarchy=[{"parent":"alpha", "child":"beta"}]))
        self.assertEqual(check_guilds([self.guild, beta]), [])

    def test_conflicting_parents(self) -> None:
        beta, gamma = self.second(), self.second("gamma")
        for root, edges in ((self.guild, [{"parent":"alpha", "child":"gamma"}]),
                            (beta, [{"parent":"beta", "child":"gamma"}]),
                            (gamma, [{"parent":"alpha", "child":"gamma"}, {"parent":"beta", "child":"gamma"}])):
            edit(root, "governance/hierarchy.yaml", lambda d: d.update(organizational_hierarchy=edges))
        self.assertIn("multiple parents", " ".join(check_guilds([self.guild, beta, gamma])))

    def test_unacknowledged_and_unknown_parent(self) -> None:
        beta = self.second()
        edit(self.guild, "governance/hierarchy.yaml", lambda d: d.update(
            organizational_hierarchy=[{"parent":"beta", "child":"alpha"}]))
        self.assertIn("acknowledgement", " ".join(check_guilds([self.guild, beta])))
        self.assertIn("unknown guild", " ".join(check_guilds([self.guild])))

    def test_organizational_cycle(self) -> None:
        beta = self.second()
        for root in (self.guild, beta):
            edit(root, "governance/hierarchy.yaml", lambda d: d.update(organizational_hierarchy=[
                {"parent":"alpha", "child":"beta"}, {"parent":"beta", "child":"alpha"}]))
        self.assertIn("circular organizational hierarchy", " ".join(check_guilds([self.guild, beta])))

    def test_exclusive_authority_covers_subdomains(self) -> None:
        beta = self.second()
        approve(self.guild, domain="commerce")
        approve(beta, domain="commerce.payments")
        self.assertIn("authority overlap", " ".join(check_guilds([self.guild, beta])))

    def test_shared_domains_require_disjoint_capabilities(self) -> None:
        beta = self.second()
        approve(self.guild, ["read"], "commerce")
        approve(beta, ["write"], "commerce")
        for root in (self.guild, beta):
            edit(root, "governance/hierarchy.yaml", lambda d: d["domain_authority"][0].update(exclusive=False))
        self.assertEqual(check_guilds([self.guild, beta]), [])
        approve(beta, ["read"], "commerce")
        edit(beta, "governance/hierarchy.yaml", lambda d: d["domain_authority"][0].update(exclusive=False))
        self.assertIn("authority overlap", " ".join(check_guilds([self.guild, beta])))

    def test_dependency_resolution_and_consumer_allowlist(self) -> None:
        beta = self.second()
        provide(self.guild, "beta")
        edit(beta, "contracts/capabilities.yaml", lambda d: d.update(requires=[{
            "guild_id":"alpha", "capability_id":"execute"}]))
        self.assertEqual(check_guilds([self.guild, beta]), [])
        edit(self.guild, "contracts/capabilities.yaml", lambda d: d["provides"][0].update(consumers=[]))
        self.assertIn("not an allowed consumer", " ".join(check_guilds([self.guild, beta])))

    def test_unknown_dependencies_and_capabilities(self) -> None:
        beta = self.second()
        edit(beta, "contracts/capabilities.yaml", lambda d: d.update(requires=[{
            "guild_id":"alpha", "capability_id":"missing"}]))
        self.assertIn("unresolved capability", " ".join(check_guilds([self.guild, beta])))
        self.assertIn("unknown dependency guild", " ".join(check_guilds([beta])))

    def test_circular_capability_dependencies(self) -> None:
        beta = self.second()
        provide(self.guild, "beta")
        provide(beta, "alpha")
        for root, provider in ((self.guild, "beta"), (beta, "alpha")):
            edit(root, "contracts/capabilities.yaml", lambda d: d.update(requires=[{
                "guild_id":provider, "capability_id":"execute"}]))
        self.assertIn("circular capability dependencies", " ".join(check_guilds([self.guild, beta])))


class GraphPrimitiveTests(unittest.TestCase):
    """Check wildcard edges and graph traversal without recursion limits."""

    def test_nats_pattern_intersections(self) -> None:
        cases = [("citadel.a.>", "citadel.a", False),
                 ("citadel.a.*", "citadel.a.x.y", False),
                 ("citadel.*.updated", "citadel.a.>", True),
                 ("citadel.a.*", "citadel.a.x", True),
                 ("citadel.a.>", "citadel.b.>", False),
                 ("citadel.a.>", "citadel.a.*", True)]
        for left, right, expected in cases:
            with self.subTest(left=left, right=right):
                self.assertEqual(subjects_overlap(left, right), expected)
                self.assertEqual(subjects_overlap(right, left), expected)

    def test_large_acyclic_graph_and_self_cycle(self) -> None:
        graph = {str(i): {str(i + 1)} for i in range(2000)}
        self.assertEqual(cycle_nodes(graph), [])
        self.assertEqual(cycle_nodes({"a":{"a"}}), ["a"])


if __name__ == "__main__":
    unittest.main()
