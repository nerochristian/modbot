const DEFAULT_BOT_INVITE_URL = 'https://discord.com/oauth2/authorize?client_id=1445812489840361656';

const configuredInviteUrl = (import.meta.env.VITE_BOT_INVITE_URL as string | undefined)?.trim();

export const BOT_INVITE_URL = configuredInviteUrl && configuredInviteUrl.length > 0
  ? configuredInviteUrl
  : DEFAULT_BOT_INVITE_URL;

export function getBotInviteUrl(guildId?: string): string {
  if (!guildId) {
    return BOT_INVITE_URL;
  }

  try {
    const url = new URL(BOT_INVITE_URL);
    url.searchParams.set('guild_id', guildId);
    url.searchParams.set('disable_guild_select', 'true');
    return url.toString();
  } catch {
    const separator = BOT_INVITE_URL.includes('?') ? '&' : '?';
    return `${BOT_INVITE_URL}${separator}guild_id=${encodeURIComponent(guildId)}&disable_guild_select=true`;
  }
}
