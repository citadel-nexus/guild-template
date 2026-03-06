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

MIT — Copyright (c) 2026 Citadel Nexus Inc
