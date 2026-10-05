<!--
# ─── CGRF Header ───────────────────────────────────────────────
# File:        AGENTS.md
# Stage:       04_HYPOTHESIZE
# SRS:         SRS-GUILD-BOOTSTRAP-001
# CAPS:        pending
# CK:          pending
# Dispatch:    user-authorized-bootstrap
# Seat:        BITS-CODEGEN
# Owner:       Citadel Nexus Inc.
# Created:     2026-10-05
# Depends:     none
# EnumType:    ConfigDoc
# EnumEdges:   DEPENDS_ON SRS-GUILD-BOOTSTRAP-001
# DAG Node:    none
# Intent:      Make agent operating boundaries explicit without granting bootstrap powers.
# ───────────────────────────────────────────────────────────────
-->

# Guild operating policy template

This repository is a governance template. Its draft policies and A1-A9 slots do
not authorize runtime actions. The user-authorized bootstrap creates this layer;
it does not assert that a VCC dispatch or external approval exists.

For subsequent guild work, read CONSTITUTION.md, CLAUDE.md, .bits/context.md,
.bits/srs_registry.yml and the applicable SRS and dispatch before acting.
Require a Ready or In progress dispatch for operational changes. If required
context is absent or contradictory, hold the action and request clarification.

Organizational parents acquire no mutation rights through parentage. Require an
explicit domain grant, an approved level, role capability and scoped delegation
where applicable. A higher A-number does not inherit lower-numbered powers.
Governance changes require scope, tests, evidence, diff review and human review.
Use the escalation routes for disputes and unavailable approvers; timeout means
HELD. Never interpret a structurally valid draft as approved authority.

Keep planned, configured, deployed and observed state distinct. Cite runnable
verification and preserve evidence. Never invent CK, CAPS or CKS grades.
Protect secrets and tenant isolation. Use Citadel Nexus Inc. for the legal owner.
No compiler command emits events, writes telemetry or changes runtime access.

In guild-template, verify with `python -m unittest discover -s tests -p 'test_*.py'` and
`python -m compiler.validate .`. See compiler/README.md for contract semantics.
