<!--
# ─── CGRF Header ───────────────────────────────────────────────
# File:        README.md
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
# Intent:      Explain the existing SDK starter and the new governance compiler.
# ───────────────────────────────────────────────────────────────
-->

# Guild Template

Starter template for building a Citadel guild. Fork this repo or use `npx @citadel-guilds/sdk init` to scaffold a new guild.

## Quick Start

```

npm install

npm run test

npm run build

```

## Structure

- `src/index.ts` — Guild manifest and hook wiring
- `src/handlers/` — Event handlers
- `tests/` — Tests using SDK mock adapters

## SDK Dependency

This template uses `@citadel-guilds/sdk` as a peer dependency. The SDK provides abstract adapters (EventBus, Storage, Auth) — the host injects real implementations at runtime.

## License

MIT — Copyright (c) 2026 Citadel Nexus Inc.

## Constitutional Governance

The governance package adds fourteen constitutional sections, separate organization
and domain-authority graphs, A1-A9 capability slots, role and service contracts,
operational mandates and NATS namespace ownership. Templates start as drafts
with no approved capability grants.

Use Python 3.11+ with no additional dependencies:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m compiler.validate .
python -m compiler.cross_guild_check .
python -m compiler.materialize ../guild-example --guild-id guild-example --name "Example Guild"
```

See [compiler/README.md](compiler/README.md) for schema and YAML support,
cross-guild checks, CLI usage and human ratification requirements. The governance
compiler is independent of the existing TypeScript SDK starter.
