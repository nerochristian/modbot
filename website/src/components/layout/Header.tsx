import { useAppStore } from '@/store/useAppStore';
import { ChevronDown, Bell, Search, LogOut, AlertTriangle, Moon, Sun, Plus, ExternalLink } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { cn, formatCount } from '@/lib/utils';
import { realApiClient } from '@/lib/api';
import { getBotInviteUrl } from '@/lib/discord';
import { useNavigate } from 'react-router-dom';
import type { AuditLogEntry } from '@/types';

const FALLBACK_AVATAR = 'https://cdn.discordapp.com/embed/avatars/0.png';
const GENERIC_INVITE_URL = getBotInviteUrl();
const NOTIFICATION_LAST_SEEN_PREFIX = 'modbot_notifications_last_seen_';

interface HeaderNotification {
  id: string;
  title: string;
  detail: string;
  timestamp: string;
}

const ACTION_LABELS: Record<string, string> = {
  config_update: 'Configuration updated',
  command_toggle: 'Command toggled',
  module_toggle: 'Module toggled',
  sync_commands: 'Commands synced',
  panic_mode_toggle: 'Panic mode toggled',
};

function formatTimeAgo(isoString: string): string {
  const timestamp = new Date(isoString).getTime();
  if (Number.isNaN(timestamp)) return 'unknown';
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function toHeaderNotification(entry: AuditLogEntry): HeaderNotification {
  const title = ACTION_LABELS[entry.action] || entry.action.replace(/_/g, ' ');
  return {
    id: entry.id,
    title,
    detail: `${entry.userName} - ${entry.target}`,
    timestamp: entry.timestamp,
  };
}

export function Header() {
  const navigate = useNavigate();
  const { user, guilds, activeGuildId, setActiveGuild, refreshGuilds, error, setError, theme, toggleTheme } = useAppStore();
  const [isServerMenuOpen, setIsServerMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [themeButtonAnimating, setThemeButtonAnimating] = useState(false);
  const [notifications, setNotifications] = useState<HeaderNotification[]>([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const themeAnimationTimerRef = useRef<number | null>(null);

  const activeServer = guilds.find((s) => s.id === activeGuildId);
  const installableGuildCount = guilds.filter((guild) => !guild.botInstalled).length;

  const loadNotifications = useCallback(async (markRead: boolean) => {
    if (!activeGuildId) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    setNotificationsLoading(true);
    try {
      const result = await realApiClient.getAuditLog(activeGuildId);
      const items = result.data.slice(0, 12).map(toHeaderNotification);
      setNotifications(items);

      const key = `${NOTIFICATION_LAST_SEEN_PREFIX}${activeGuildId}`;
      const nowIso = new Date().toISOString();
      const lastSeenRaw = localStorage.getItem(key);
      const lastSeen = lastSeenRaw ? Date.parse(lastSeenRaw) : 0;
      const unread = items.filter((item) => {
        const ts = Date.parse(item.timestamp);
        return Number.isFinite(ts) && ts > lastSeen;
      }).length;

      if (markRead) {
        localStorage.setItem(key, nowIso);
        setUnreadCount(0);
      } else {
        setUnreadCount(unread);
      }
    } catch {
      setNotifications([]);
      setUnreadCount(0);
    } finally {
      setNotificationsLoading(false);
    }
  }, [activeGuildId]);

  useEffect(() => {
    return () => {
      if (themeAnimationTimerRef.current !== null) {
        window.clearTimeout(themeAnimationTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isServerMenuOpen) {
      return;
    }
    void refreshGuilds();
  }, [isServerMenuOpen, refreshGuilds]);

  useEffect(() => {
    setIsNotificationsOpen(false);
    void loadNotifications(false);
  }, [activeGuildId, loadNotifications]);

  useEffect(() => {
    if (!isNotificationsOpen) {
      return;
    }
    void loadNotifications(true);
  }, [isNotificationsOpen, activeGuildId, loadNotifications]);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await realApiClient.logout();
    } catch {
      // ignore and continue to clear local UI session
    } finally {
      window.location.href = '/';
    }
  };

  const handleThemeToggle = () => {
    if (themeAnimationTimerRef.current !== null) {
      window.clearTimeout(themeAnimationTimerRef.current);
    }
    setThemeButtonAnimating(true);
    toggleTheme();
    themeAnimationTimerRef.current = window.setTimeout(() => {
      setThemeButtonAnimating(false);
      themeAnimationTimerRef.current = null;
    }, 520);
  };

  return (
    <>
      <header className="h-16 bg-card-bg border-b border-cream-300 flex items-center justify-between px-6 shrink-0 sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-4">
          {/* Server Selector */}
          <div className="relative">
            <button
              onClick={() => setIsServerMenuOpen(!isServerMenuOpen)}
              className="flex items-center gap-3 bg-app-bg hover:bg-cream-200 transition-colors px-4 py-2 rounded-xl border border-cream-300 shadow-sm"
            >
              {activeServer ? (
                <>
                  <img src={activeServer.icon || FALLBACK_AVATAR} alt={activeServer.name} className="w-6 h-6 rounded-full" />
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-slate-800">{activeServer.name}</span>
                    {!activeServer.botInstalled && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-amber-100 text-amber-700 font-semibold uppercase tracking-wide">
                        Not added
                      </span>
                    )}
                  </div>
                </>
              ) : (
                <span className="font-semibold text-slate-500">Select Server</span>
              )}
              <ChevronDown className="w-4 h-4 text-slate-500" />
            </button>

            {isServerMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setIsServerMenuOpen(false)} />
                <div className="absolute top-full left-0 mt-2 w-80 max-w-[calc(100vw-1rem)] bg-card-bg rounded-2xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] border border-cream-300 py-2 z-50">
                  <div className="px-3 pb-2 mb-1 border-b border-cream-200">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Your Servers</p>
                    {installableGuildCount > 0 && (
                      <p className="text-[11px] text-slate-500 mt-1">
                        {installableGuildCount} server{installableGuildCount === 1 ? '' : 's'} still need Modbot.
                      </p>
                    )}
                  </div>
                  {guilds.length === 0 ? (
                    <div className="px-4 py-4 space-y-3">
                      <p className="text-sm text-slate-600">No manageable Discord servers found.</p>
                      <a
                        href={GENERIC_INVITE_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="w-full inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 transition-colors"
                      >
                        <Plus className="w-4 h-4" />
                        Add Modbot to a Server
                      </a>
                    </div>
                  ) : (
                    <div className="max-h-72 overflow-y-auto">
                    {guilds.map((server) => (
                      <div key={server.id} className="px-2">
                        <div
                          className={cn(
                            'grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 rounded-xl p-1',
                            activeGuildId === server.id && 'bg-indigo-50'
                          )}
                        >
                          <button
                            onClick={() => {
                              setActiveGuild(server.id);
                              setIsServerMenuOpen(false);
                            }}
                            className="min-w-0 flex-1 flex items-center gap-3 px-2 py-1.5 hover:bg-app-bg rounded-lg transition-colors text-left"
                          >
                            <img src={server.icon || FALLBACK_AVATAR} alt={server.name} className="w-8 h-8 rounded-full" />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-slate-800 truncate">{server.name}</div>
                              <div className="text-xs text-slate-500">{formatCount(server.memberCount)} members</div>
                            </div>
                            {activeGuildId === server.id && (
                              <div className="w-2 h-2 rounded-full bg-indigo-600" />
                            )}
                          </button>
                          {!server.botInstalled && (
                            <a
                              href={getBotInviteUrl(server.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={() => setIsServerMenuOpen(false)}
                              className="shrink-0 whitespace-nowrap inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#5865F2] text-white text-[10px] font-semibold hover:bg-[#4752C4] transition-colors"
                            >
                              <Plus className="w-3.5 h-3.5" />
                              Add Bot
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                    </div>
                  )}
                  <div className="px-3 pt-2 mt-1 border-t border-cream-200">
                    <a
                      href={GENERIC_INVITE_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => setIsServerMenuOpen(false)}
                      className="inline-flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
                    >
                      Open full invite link
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative hidden md:block">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search..."
              className="pl-9 pr-4 py-2 bg-app-bg border border-cream-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all w-48"
            />
          </div>

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={() => setIsNotificationsOpen((prev) => !prev)}
              className="relative p-2 text-slate-500 hover:bg-app-bg rounded-xl transition-colors"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {isNotificationsOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setIsNotificationsOpen(false)} />
                <div className="absolute top-full right-0 mt-2 w-80 max-w-[calc(100vw-1rem)] bg-card-bg rounded-2xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] border border-cream-300 py-2 z-50">
                  <div className="px-3 pb-2 mb-1 border-b border-cream-200">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Notifications</p>
                  </div>
                  {notificationsLoading ? (
                    <div className="px-4 py-6 text-sm text-slate-500">Loading notifications...</div>
                  ) : notifications.length === 0 ? (
                    <div className="px-4 py-6 text-sm text-slate-500">No recent notifications.</div>
                  ) : (
                    <div className="max-h-72 overflow-y-auto">
                      {notifications.map((item) => (
                        <button
                          key={item.id}
                          onClick={() => {
                            setIsNotificationsOpen(false);
                            navigate('/dashboard/audit');
                          }}
                          className="w-full text-left px-3 py-2.5 hover:bg-app-bg transition-colors"
                        >
                          <p className="text-sm font-semibold text-slate-800 truncate">{item.title}</p>
                          <p className="text-xs text-slate-500 truncate">{item.detail}</p>
                          <p className="text-[11px] text-slate-400 mt-1">{formatTimeAgo(item.timestamp)}</p>
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="px-3 pt-2 mt-1 border-t border-cream-200">
                    <button
                      onClick={() => {
                        setIsNotificationsOpen(false);
                        navigate('/dashboard/audit');
                      }}
                      className="text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
                    >
                      View all activity
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Theme Toggle */}
          <button
            onClick={handleThemeToggle}
            className={cn(
              'theme-toggle-btn p-2 text-slate-500 hover:bg-app-bg rounded-xl transition-colors',
              themeButtonAnimating && 'theme-toggle-btn--animating'
            )}
            title="Toggle Theme"
          >
            <span className="relative block h-5 w-5">
              <Sun
                className={cn(
                  'theme-toggle-icon absolute inset-0 h-5 w-5',
                  theme === 'dark'
                    ? 'opacity-100 rotate-0 scale-100 text-amber-300'
                    : 'opacity-0 -rotate-90 scale-50 text-amber-300'
                )}
              />
              <Moon
                className={cn(
                  'theme-toggle-icon absolute inset-0 h-5 w-5',
                  theme === 'dark'
                    ? 'opacity-0 rotate-90 scale-50 text-slate-400'
                    : 'opacity-100 rotate-0 scale-100 text-slate-500'
                )}
              />
            </span>
          </button>

          {/* User Profile */}
          <div className="relative">
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-3 hover:bg-app-bg p-1.5 rounded-xl transition-colors"
            >
              <div className="text-right hidden sm:block">
                <div className="text-sm font-semibold text-slate-900">{user?.username}</div>
              </div>
              <img src={user?.avatar || FALLBACK_AVATAR} alt={user?.username} className="w-8 h-8 rounded-full border-2 border-white shadow-sm" />
            </button>

            {isUserMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setIsUserMenuOpen(false)} />
                <div className="absolute top-full right-0 mt-2 w-48 bg-card-bg rounded-2xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] border border-cream-300 py-2 z-50">
                  <button
                    onClick={handleLogout}
                    disabled={loggingOut}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors text-left font-medium"
                  >
                    <LogOut className="w-4 h-4" />
                    {loggingOut ? 'Logging out...' : 'Logout'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3 flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
          <p className="text-sm text-red-700 flex-1">{error}</p>
          <button onClick={() => setError(null)} className="text-xs font-medium text-red-600 hover:text-red-800">
            Dismiss
          </button>
        </div>
      )}
    </>
  );
}
