import type { GuildManifest, GuildContext, GuildEvent } from '@citadel-guilds/sdk';
import { handleExampleEvent } from './handlers/example';

export const manifest: GuildManifest = {
  id: 'my-guild',
  name: 'My Guild',
  version: '0.1.0',
  description: 'A new Citadel guild built from the template.',
  eventNamespace: 'citadel.my-guild',
  requiredPermissions: ['events:publish', 'events:subscribe', 'storage:read'],
  hooks: {
    onActivate: async (ctx: GuildContext) => {
      ctx.logger.info(`${manifest.name} activated`);
    },
    onEvent: async (ctx: GuildContext, event: GuildEvent) => {
      await handleExampleEvent(ctx, event);
    },
  },
};
