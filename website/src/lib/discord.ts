import { AUTH_BASE } from '@/lib/api';

const INVITE_BASE_URL = AUTH_BASE ? `${AUTH_BASE}/auth/invite` : '/auth/invite';

export const BOT_INVITE_URL = INVITE_BASE_URL;

export function getBotInviteUrl(guildId?: string): string {
  if (!guildId) {
    return BOT_INVITE_URL;
  }

  try {
    const url = new URL(BOT_INVITE_URL, window.location.origin);
    url.searchParams.set('guild_id', guildId);
    url.searchParams.set('disable_guild_select', 'true');
    return BOT_INVITE_URL.startsWith('http') ? url.toString() : `${url.pathname}${url.search}`;
  } catch {
    const separator = BOT_INVITE_URL.includes('?') ? '&' : '?';
    return `${BOT_INVITE_URL}${separator}guild_id=${encodeURIComponent(guildId)}&disable_guild_select=true`;
  }
}
