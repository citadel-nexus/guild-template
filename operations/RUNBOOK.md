<!--
# ─── CGRF Header ───────────────────────────────────────────────
# File:        operations/RUNBOOK.md
# Stage:       06_PLAN
# SRS:         SRS-GUILD-BOOTSTRAP-001
# CAPS:        pending
# CK:          pending
# Dispatch:    user-authorized-bootstrap
# Seat:        BITS-CODEGEN
# Owner:       Citadel Nexus Inc.
# Created:     2026-10-05
# Depends:     none
# EnumType:    Doc
# EnumEdges:   DEPENDS_ON SRS-GUILD-BOOTSTRAP-001
# DAG Node:    none
# Intent:      Provide reproducible review and incident handling steps.
# ───────────────────────────────────────────────────────────────
-->

# Governance runbook

1. Record the guild set, intended change, SRS and dispatch authorization.
2. Run `python -m compiler.validate .` and retain diagnostics.
3. Run `python -m compiler.cross_guild_check PATH_A PATH_B` for the complete set.
4. Run `python -m unittest discover -s tests -p 'test_*.py'` in guild-template.
5. Obtain human review and record evidence before ratification or activation.
6. On conflict, hold affected actions and use governance/escalation.yaml.
7. On regression, revert the reviewed change and repeat validation.

These are proposed operational steps; commands do not contact external services.
The SLO is a target, not an observed measurement. Configure telemetry separately.
