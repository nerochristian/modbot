const API_BASE = '';

class ApiClient {
  async request(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (res.status === 401) {
      window.location.href = '/';
      throw new Error('Unauthorized');
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: res.statusText }));
      throw new Error(err.message || 'API Error');
    }
    return res.json();
  }

  getMe() { return this.request('/api/me'); }
  getGuilds() { return this.request('/api/guilds'); }
  getGuild(id) { return this.request(`/api/guilds/${id}`); }
  getGuildConfig(id) { return this.request(`/api/guilds/${id}/config`); }
  updateGuildConfig(id, data) {
    return this.request(`/api/guilds/${id}/config`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }
  getGuildChannels(id) { return this.request(`/api/guilds/${id}/channels`); }
  getGuildRoles(id) { return this.request(`/api/guilds/${id}/roles`); }
  getGuildCases(id, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request(`/api/guilds/${id}/cases${qs ? `?${qs}` : ''}`);
  }
  getGuildStats(id) { return this.request(`/api/guilds/${id}/stats`); }
  getGuildSetup(id) { return this.request(`/api/guilds/${id}/setup`); }
  getGuildAudit(id) { return this.request(`/api/guilds/${id}/audit`); }
  getGuildWarnings(id) { return this.request(`/api/guilds/${id}/warnings`); }
  syncCommands(id) {
    return this.request(`/api/guilds/${id}/commands/sync`, { method: 'POST' });
  }
  logout() { return this.request('/auth/logout', { method: 'GET' }); }
}

export const api = new ApiClient();
