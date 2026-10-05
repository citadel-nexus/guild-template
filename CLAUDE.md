<!--
# ─── CGRF Header ───────────────────────────────────────────────
# File:        CLAUDE.md
# Stage:       04_HYPOTHESIZE
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
# Intent:      Explain human review and ratification of generated guild contracts.
# ───────────────────────────────────────────────────────────────
-->

# Human companion template

The constitution defines enduring powers; AGENTS.md defines operating policy.
Machine contracts make those declarations checkable. Replace draft prompts,
assign human stewards, approve exact capability mappings and review the diff
before ratifying a guild. Structural validation is not an authorization decision.

Review organizational and domain graphs independently. Review canonical event
names and deprecated aliases together. Resolve conflicts explicitly rather than
silently choosing a parent, namespace or source of truth.

Use `python -m compiler.materialize TARGET --guild-id guild-example --name "Example Guild"`
to create a draft skeleton, then edit its constitution and contracts. The default
namespace is a draft reservation only. Cross-check the complete guild set with
`python -m compiler.cross_guild_check PATH_A PATH_B` before adoption.

A1-A9 are configurable slots pending operator approval; no production mapping
was available to this bootstrap. This package performs local checks only.
