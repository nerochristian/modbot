import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useAppStore } from '@/store/useAppStore';
import { Bot, ExternalLink, RefreshCw } from 'lucide-react';
import { getBotInviteUrl } from '@/lib/discord';
import { useEffect, useState } from 'react';

interface EmptyGuildStateProps {
  title: string;
  description: string;
  inviteUrl: string;
  onRefresh: () => Promise<void>;
}

function EmptyGuildState({ title, description, inviteUrl, onRefresh }: EmptyGuildStateProps) {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="max-w-xl w-full text-center bg-card-bg border border-cream-300 rounded-3xl p-10 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.12)]">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 mb-5">
          <Bot className="w-7 h-7" />
        </div>
        <h2 className="text-2xl font-display font-bold text-slate-800 tracking-tight">{title}</h2>
        <p className="text-sm text-slate-500 mt-2 mb-6">{description}</p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <a
            href={inviteUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#5865F2] hover:bg-[#4752C4] text-white text-sm font-semibold transition-colors"
          >
            Add Modbot to Server
            <ExternalLink className="w-4 h-4" />
          </a>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl border border-cream-300 bg-white hover:bg-cream-50 text-slate-700 text-sm font-semibold transition-colors disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Checking...' : 'Refresh Status'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function DashboardLayout() {
  const location = useLocation();
  const { loading, guilds, activeGuildId, refreshGuilds, setActiveGuild } = useAppStore();
  const activeGuild = guilds.find((guild) => guild.id === activeGuildId);

  useEffect(() => {
    if (loading) {
      return;
    }
    const params = new URLSearchParams(location.search);
    const requestedGuildId = params.get('guild');
    if (!requestedGuildId || requestedGuildId === activeGuildId) {
      return;
    }
    if (!guilds.some((guild) => guild.id === requestedGuildId)) {
      return;
    }
    setActiveGuild(requestedGuildId);
  }, [activeGuildId, guilds, loading, location.search, setActiveGuild]);

  useEffect(() => {
    if (loading) {
      return;
    }

    void refreshGuilds();

    const handleFocus = () => {
      void refreshGuilds();
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void refreshGuilds();
      }
    };

    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [loading, refreshGuilds]);

  const showEmptyState = !loading && guilds.length === 0;
  const showSelectState = !loading && guilds.length > 0 && !activeGuildId;
  const showInstallState = !loading && Boolean(activeGuild && !activeGuild.botInstalled);

  return (
    <div className="flex h-screen w-full bg-app-bg overflow-hidden text-slate-800">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 lg:p-10">
          <div className="max-w-7xl mx-auto">
            {showEmptyState && (
              <EmptyGuildState
                title="No Server Connected Yet"
                description="Add Modbot to a Discord server you manage, then click Refresh Status."
                inviteUrl={getBotInviteUrl()}
                onRefresh={refreshGuilds}
              />
            )}
            {showSelectState && (
              <EmptyGuildState
                title="Select a Server"
                description="Pick a server from the top-left dropdown to start configuring your dashboard."
                inviteUrl={getBotInviteUrl()}
                onRefresh={refreshGuilds}
              />
            )}
            {showInstallState && activeGuild && (
              <EmptyGuildState
                title={`Modbot Not Added to ${activeGuild.name}`}
                description="If you just invited the bot, click Refresh Status. Discord can take a few seconds to sync."
                inviteUrl={getBotInviteUrl(activeGuild.id)}
                onRefresh={refreshGuilds}
              />
            )}
            {!showEmptyState && !showSelectState && !showInstallState && <Outlet />}
          </div>
        </main>
      </div>
    </div>
  );
}
