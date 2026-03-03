import { create } from 'zustand';
import type { AuthUser, BotCapabilities, GuildConfig } from '@/types';
import type { ApiClient } from '@/lib/api';
import { realApiClient } from '@/lib/api';

// Use real API client — backend serves /api/* routes
const api: ApiClient = realApiClient;

interface AppState {
  // Auth
  user: AuthUser | null;
  loading: boolean;
  error: string | null;

  // Guilds
  guilds: { id: string; name: string; icon: string | null; memberCount: number; botInstalled: boolean }[];
  activeGuildId: string | null;

  // Capabilities (global, fetched once)
  capabilities: BotCapabilities | null;

  // Guild config (fetched per guild)
  config: GuildConfig | null;
  configVersion: number;
  configDirty: boolean;

  // Actions
  initialize: () => Promise<void>;
  setActiveGuild: (id: string) => void;
  fetchConfig: (guildId: string) => Promise<void>;
  updateConfigLocal: (partial: Partial<GuildConfig>) => void;
  saveConfig: () => Promise<void>;
  discardChanges: () => void;
  setError: (err: string | null) => void;
}

let originalConfig: GuildConfig | null = null;

export const useAppStore = create<AppState>((set, get) => ({
  user: null,
  loading: true,
  error: null,
  guilds: [],
  activeGuildId: null,
  capabilities: null,
  config: null,
  configVersion: 0,
  configDirty: false,

  initialize: async () => {
    try {
      set({ loading: true, error: null });

      // Try to fetch user — if 401, user is not logged in
      let user: AuthUser;
      try {
        user = await api.getMe();
      } catch (err: any) {
        if (err?.status === 401) {
          // Not logged in — this is expected
          set({ loading: false, user: null });
          return;
        }
        throw err;
      }

      const guilds = user.guilds.filter(g => g.botInstalled);

      let capabilities: BotCapabilities | null = null;
      try {
        capabilities = await api.getCapabilities();
      } catch {
        // Bot might not expose capabilities yet
      }

      set({
        user,
        guilds,
        capabilities,
        activeGuildId: guilds[0]?.id || null,
        loading: false,
      });

      if (guilds[0]) {
        await get().fetchConfig(guilds[0].id);
      }
    } catch (err) {
      set({ loading: false, error: err instanceof Error ? err.message : 'Failed to initialize' });
    }
  },

  setActiveGuild: (id: string) => {
    set({ activeGuildId: id, config: null, configDirty: false });
    get().fetchConfig(id);
  },

  fetchConfig: async (guildId: string) => {
    try {
      const { data, version } = await api.getConfig(guildId);
      originalConfig = JSON.parse(JSON.stringify(data));
      set({ config: data, configVersion: version || data.version, configDirty: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to fetch config' });
    }
  },

  updateConfigLocal: (partial) => {
    const current = get().config;
    if (!current) return;
    set({ config: { ...current, ...partial }, configDirty: true });
  },

  saveConfig: async () => {
    const { config, configVersion, activeGuildId } = get();
    if (!config || !activeGuildId) return;
    try {
      const { data, version } = await api.updateConfig(activeGuildId, config, configVersion);
      originalConfig = JSON.parse(JSON.stringify(data));
      set({ config: data, configVersion: version || data.version, configDirty: false, error: null });
    } catch (err) {
      if (err instanceof Error && err.message.includes('conflict')) {
        set({ error: 'Config was updated by someone else. Please refresh and try again.' });
      } else {
        set({ error: err instanceof Error ? err.message : 'Failed to save config' });
      }
      throw err;
    }
  },

  discardChanges: () => {
    if (originalConfig) {
      set({ config: JSON.parse(JSON.stringify(originalConfig)), configDirty: false });
    }
  },

  setError: (err) => set({ error: err }),
}));
