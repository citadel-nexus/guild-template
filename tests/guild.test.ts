import { describe, it, expect } from 'vitest';
import { MockEventBus, MockStorage, MockAuth } from '@citadel-guilds/sdk';
import type { GuildContext } from '@citadel-guilds/sdk';
import { manifest } from '../src/index';
import { handleExampleEvent } from '../src/handlers/example';

function createTestContext(): GuildContext {
  return {
    guildId: manifest.id,
    eventBus: new MockEventBus(),
    storage: new MockStorage(),
    auth: new MockAuth(),
    logger: { info: () => {}, warn: () => {}, error: () => {} },
  };
}

describe('Guild Template', () => {
  it('should have a valid manifest', () => {
    expect(manifest.id).toBeTruthy();
    expect(manifest.name).toBeTruthy();
    expect(manifest.eventNamespace).toBeTruthy();
  });

  it('should handle events and publish echo', async () => {
    const ctx = createTestContext();
    const bus = ctx.eventBus as MockEventBus;

    await handleExampleEvent(ctx, {
      id: 'test-1',
      type: 'test.event',
      source: 'test',
      timestamp: new Date().toISOString(),
      payload: { value: 42 },
    });

    expect(bus.published.length).toBe(1);
    expect(bus.published[0].type).toContain('echo');
  });
});
