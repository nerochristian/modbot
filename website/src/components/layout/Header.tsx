import { useAppStore } from '@/store/useAppStore';
import { ChevronDown, Bell, Search, LogOut, AlertTriangle, Moon, Sun } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { realApiClient } from '@/lib/api';

export function Header() {
  const { user, guilds, activeGuildId, setActiveGuild, error, setError, theme, toggleTheme } = useAppStore();
  const [isServerMenuOpen, setIsServerMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [themeButtonAnimating, setThemeButtonAnimating] = useState(false);
  const themeAnimationTimerRef = useRef<number | null>(null);

  const activeServer = guilds.find((s) => s.id === activeGuildId);

  useEffect(() => {
    return () => {
      if (themeAnimationTimerRef.current !== null) {
        window.clearTimeout(themeAnimationTimerRef.current);
      }
    };
  }, []);

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
                  <img src={activeServer.icon || 'https://cdn.discordapp.com/embed/avatars/0.png'} alt={activeServer.name} className="w-6 h-6 rounded-full" />
                  <span className="font-semibold text-sm text-slate-800">{activeServer.name}</span>
                </>
              ) : (
                <span className="font-semibold text-slate-500">Select Server</span>
              )}
              <ChevronDown className="w-4 h-4 text-slate-500" />
            </button>

            {isServerMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setIsServerMenuOpen(false)} />
                <div className="absolute top-full left-0 mt-2 w-72 bg-card-bg rounded-2xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] border border-cream-300 py-2 z-50">
                  <div className="px-3 pb-2 mb-1 border-b border-cream-200">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Your Servers</p>
                  </div>
                  {guilds.map((server) => (
                    <button
                      key={server.id}
                      onClick={() => {
                        setActiveGuild(server.id);
                        setIsServerMenuOpen(false);
                      }}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-2.5 hover:bg-app-bg transition-colors text-left',
                        activeGuildId === server.id && 'bg-indigo-50'
                      )}
                    >
                      <img src={server.icon || 'https://cdn.discordapp.com/embed/avatars/0.png'} alt={server.name} className="w-8 h-8 rounded-full" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-800 truncate">{server.name}</div>
                        <div className="text-xs text-slate-500">{server.memberCount.toLocaleString()} members</div>
                      </div>
                      {activeGuildId === server.id && (
                        <div className="w-2 h-2 rounded-full bg-indigo-600" />
                      )}
                    </button>
                  ))}
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
          <button className="relative p-2 text-slate-500 hover:bg-app-bg rounded-xl transition-colors">
            <Bell className="w-5 h-5" />
          </button>

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
              <img src={user?.avatar || 'https://cdn.discordapp.com/embed/avatars/0.png'} alt={user?.username} className="w-8 h-8 rounded-full border-2 border-white shadow-sm" />
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
