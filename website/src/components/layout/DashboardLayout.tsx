import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useAppStore } from '@/store/useAppStore';
import { Bot, ExternalLink } from 'lucide-react';
import { getBotInviteUrl } from '@/lib/discord';

function EmptyGuildState() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="max-w-xl w-full text-center bg-card-bg border border-cream-300 rounded-3xl p-10 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.12)]">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 mb-5">
          <Bot className="w-7 h-7" />
        </div>
        <h2 className="text-2xl font-display font-bold text-slate-800 tracking-tight">No Server Connected Yet</h2>
        <p className="text-sm text-slate-500 mt-2 mb-6">
          Add Modbot to a Discord server you manage, then refresh this page and select it from the server dropdown.
        </p>
        <a
          href={getBotInviteUrl()}
          className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#5865F2] hover:bg-[#4752C4] text-white text-sm font-semibold transition-colors"
        >
          Add Modbot to Server
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </div>
  );
}

export function DashboardLayout() {
  const { loading, guilds, activeGuildId } = useAppStore();
  const showEmptyState = !loading && guilds.length === 0;
  const showSelectState = !loading && guilds.length > 0 && !activeGuildId;

  return (
    <div className="flex h-screen w-full bg-app-bg overflow-hidden text-slate-800">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 lg:p-10">
          <div className="max-w-7xl mx-auto">
            {showEmptyState || showSelectState ? <EmptyGuildState /> : <Outlet />}
          </div>
        </main>
      </div>
    </div>
  );
}
