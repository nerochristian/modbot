const API_BASE = '';

class ApiClient {
  async request(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    const contentType = res.headers.get('content-type') || '';
    if (res.status === 401) {
      window.location.href = '/';
      throw new Error('Unauthorized');
    }
    if (!contentType.includes('application/json')) {
      throw new Error(`Expected JSON from ${path}, got ${contentType || 'unknown content type'}`);
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
  logout() { return this.request('/api/auth/logout', { method: 'POST' }); }
}

export const api = new ApiClient();
