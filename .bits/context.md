<!--
# ─── CGRF Header ───────────────────────────────────────────────
# File:        .bits/context.md
# Stage:       11_COMMIT
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
# Intent:      Record explicit bootstrap scope without fabricating a dispatch.
# ───────────────────────────────────────────────────────────────
-->

# Bootstrap context

Scope: create the constitutional governance template and local stdlib compiler.
Authorization: explicit user bootstrap request; no pre-existing VCC dispatch is
claimed. `user-authorized-bootstrap` is a provenance marker, not a VCC status.
SRS-GUILD-BOOTSTRAP-001 is a local bootstrap scope identifier.

Do: keep drafts without grants, validate references, preserve existing SDK code.
Do not: call private services, emit events, assign unapproved authority, claim
live telemetry or manufacture CK/CAPS/CKS scores.

Next: the human operator defines the A1-A9 mapping, resolves constitution prompts
and supplies operational SRS/dispatch records before enabling guild actions.
