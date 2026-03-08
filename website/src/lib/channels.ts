import type { DiscordChannel } from '@/types';

const MESSAGE_DESTINATION_CHANNEL_TYPES = new Set([0, 5]); // text, announcement

function normalizeType(value: number | string): number {
  if (typeof value === 'number') return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : -1;
}

export function isMessageCapableChannel(channel: Pick<DiscordChannel, 'type'>): boolean {
  return MESSAGE_DESTINATION_CHANNEL_TYPES.has(normalizeType(channel.type));
}

export function toChannelOptions(channels: DiscordChannel[]): { label: string; value: string }[] {
  return channels
    .filter(isMessageCapableChannel)
    .map((channel) => ({ label: `#${channel.name}`, value: channel.id }));
}
