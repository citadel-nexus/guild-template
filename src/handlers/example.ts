import type { GuildContext, GuildEvent } from '@citadel-guilds/sdk';

export async function handleExampleEvent(
  ctx: GuildContext,
  event: GuildEvent,
): Promise<void> {
  ctx.logger.info(`Received event: ${event.type}`, event.payload);

  // Example: echo the event back on a different subject
  await ctx.eventBus.publish(
    `${ctx.guildId}.echo`,
    {
      id: crypto.randomUUID(),
      type: `${ctx.guildId}.echo`,
      source: ctx.guildId,
      timestamp: new Date().toISOString(),
      payload: { original: event.id },
    },
  );
}
