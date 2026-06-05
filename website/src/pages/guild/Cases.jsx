import { useState, useEffect } from 'react'
import {
  Gavel, Search, Filter, ChevronLeft, ChevronRight,
  User, Clock, AlertTriangle, Ban, UserMinus, VolumeX,
  AlertCircle, Loader2
} from 'lucide-react'
import { useGuild } from '../GuildDashboard'
import { api } from '../../api'

const ACTION_ICONS = {
  ban: { icon: Ban, color: '#ff4d6a', label: 'Ban' },
  kick: { icon: UserMinus, color: '#f97316', label: 'Kick' },
  mute: { icon: VolumeX, color: '#ffb800', label: 'Mute' },
  timeout: { icon: VolumeX, color: '#ffb800', label: 'Timeout' },
  warn: { icon: AlertTriangle, color: '#ffb800', label: 'Warn' },
  unban: { icon: Ban, color: '#00d68f', label: 'Unban' },
  unmute: { icon: VolumeX, color: '#00d68f', label: 'Unmute' },
}

function formatDate(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function Cases() {
  const { guildId } = useGuild()
  const [cases, setCases] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  useEffect(() => {
    setLoading(true)
    api.getGuildCases(guildId, { page, limit: 20, q: search || undefined })
      .then(data => {
        setCases(data.cases || data || [])
        setTotalPages(data.totalPages || 1)
      })
      .catch(() => setCases([]))
      .finally(() => setLoading(false))
  }, [guildId, page, search])

  const getActionMeta = (action) => {
    const key = (action || '').toLowerCase()
    return ACTION_ICONS[key] || { icon: AlertCircle, color: 'var(--text-muted)', label: action || 'Unknown' }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Moderation Cases</h1>
        <p className="page-subtitle">View all moderation actions taken in this server.</p>
      </div>

      {/* Search */}
      <div className="cases-toolbar">
        <div className="cases-search">
          <Search size={16} />
          <input
            type="text"
            className="input"
            placeholder="Search cases by user or reason..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="empty-state">
          <Loader2 size={32} className="spin" />
          <p>Loading cases...</p>
        </div>
      ) : cases.length === 0 ? (
        <div className="empty-state">
          <Gavel size={48} />
          <h3>No cases found</h3>
          <p>No moderation cases match your search criteria.</p>
        </div>
      ) : (
        <>
          <div className="cases-table-wrap">
            <table className="case-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Action</th>
                  <th>User</th>
                  <th>Moderator</th>
                  <th>Reason</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c, i) => {
                  const meta = getActionMeta(c.action || c.type)
                  const ActionIcon = meta.icon
                  return (
                    <tr key={c.id || c.case_id || i}>
                      <td>
                        <span className="case-id">#{c.case_id || c.id || i + 1}</span>
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            background: `${meta.color}18`,
                            color: meta.color,
                          }}
                        >
                          <ActionIcon size={12} />
                          {meta.label}
                        </span>
                      </td>
                      <td>
                        <div className="case-user">
                          <div className="case-user-avatar" />
                          <span>{c.target_name || c.user || c.target || 'Unknown'}</span>
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                        {c.moderator_name || c.moderator || c.mod || 'System'}
                      </td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', maxWidth: 200 }}>
                        <span style={{ 
                          display: 'block',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: 200,
                        }}>
                          {c.reason || 'No reason provided'}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {formatDate(c.created_at || c.timestamp || c.date)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="cases-pagination">
              <button
                className="btn btn-ghost btn-sm"
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                <ChevronLeft size={16} /> Previous
              </button>
              <span className="cases-page-info">
                Page {page} of {totalPages}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
