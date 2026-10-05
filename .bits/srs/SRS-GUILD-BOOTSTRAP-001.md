<!--
# ─── CGRF Header ───────────────────────────────────────────────
# File:        .bits/srs/SRS-GUILD-BOOTSTRAP-001.md
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
# Intent:      Record the user-authorized bootstrap scope and testable acceptance criteria.
# ───────────────────────────────────────────────────────────────
-->

# Constitutional governance bootstrap scope

This local SRS records the explicit user request to create governance in the
previously ungoverned guild-template repository. It is not an externally issued
VCC dispatch. The provenance marker is `user-authorized-bootstrap`; no Ready
status or external approval is asserted.

## Objective

Deliver seven machine-readable schemas, a Python 3.11+ standard-library compiler,
four unittest modules and inheritable governance templates. Preserve the existing
TypeScript starter and license. Use the exact paths named in the bootstrap task;
CGRF stages classify those files rather than adding private CKET directories.

## Acceptance

- Represent all fourteen constitutional sections and require them in Markdown.
- Keep organizational hierarchy separate from domain mutation authority.
- Define A1-A9 as configurable slots with no unapproved capability grants.
- Validate required files, supported YAML, CGRF envelopes and local references.
- Detect namespace collisions, parent conflicts, domain overlaps and dependency cycles.
- Generate independently valid draft guilds without overwriting existing paths.
- Run unittest with no third-party runtime or test dependencies.

## Verification

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m compiler.validate .
python -m compiler.cross_guild_check .
python -m mypy --strict compiler
python -m ruff check compiler tests
```

The last two tools are optional developer checks available in this session; they
are not compiler dependencies. Generation and CLI failure paths are exercised by
unittest. No live service, telemetry, external approval or deployment is asserted.

## Remaining human decisions

Ratify constitutional answers, supply production A1-A9 capability definitions,
assign operational SRS/dispatch records and approve runtime integration separately.
CK, CAPS and CKS remain pending. Structural validity alone grants no powers.
