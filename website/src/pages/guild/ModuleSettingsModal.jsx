import { useState, useEffect, useCallback } from 'react'
import {
  X, Save, Loader2, CheckCircle2, XCircle, SlidersHorizontal
} from 'lucide-react'
import { useGuild } from './GuildContext'
import { api } from '../../api'

export default function ModuleSettingsModal({ module, onClose }) {
  const { guildId, config, updateConfig } = useGuild()
  const [channels, setChannels] = useState([])
  const [roles, setRoles] = useState([])
  const [values, setValues] = useState({})
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const [loadingPickers, setLoadingPickers] = useState(true)

  // Fetch channels/roles for pickers
  useEffect(() => {
    Promise.all([
      api.getGuildChannels(guildId).catch(() => []),
      api.getGuildRoles(guildId).catch(() => []),
    ]).then(([ch, ro]) => {
      setChannels(ch)
      setRoles(ro)
    }).finally(() => setLoadingPickers(false))
  }, [guildId])

  // Load current values from config
  useEffect(() => {
    const moduleConfig = config?.modules?.[module.id] || {}
    const settings = moduleConfig.settings || {}
    setValues({ ...settings })
  }, [config, module.id])

  // Get the settings schema from the module capabilities
  const capabilities = config?.capabilities || {}
  const moduleCap = capabilities[module.id] || {}
  const schema = moduleCap.settingsSchema || module.settingsSchema || []

  // Group schema fields by section
  const sections = {}
  schema.forEach(field => {
    const sec = field.section || 'General'
    if (!sections[sec]) sections[sec] = []
    sections[sec].push(field)
  })

  const handleChange = useCallback((key, value) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = {
        modules: {
          [module.id]: {
            settings: values,
          },
        },
      }
      await updateConfig(payload)
      setToast({ message: 'Settings saved', type: 'success' })
    } catch {
      setToast({ message: 'Failed to save', type: 'error' })
    }
    setSaving(false)
    setTimeout(() => setToast(null), 2500)
  }

  // Close on escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const renderField = (field) => {
    const val = values[field.key]

    switch (field.type) {
      case 'boolean':
        return (
          <div className="settings-row" key={field.key}>
            <div>
              <div className="settings-row-label">{field.label}</div>
              {field.description && <div className="settings-row-desc">{field.description}</div>}
            </div>
            <button
              className={`mp-toggle ${val ? 'on' : ''}`}
              onClick={() => handleChange(field.key, !val)}
            >
              <span className="mp-toggle-thumb" />
            </button>
          </div>
        )

      case 'number':
        return (
          <div className="modal-field" key={field.key}>
            <label className="modal-field-label">{field.label}</label>
            <input
              type="number"
              className="input"
              value={val ?? field.defaultValue ?? ''}
              min={field.constraints?.min}
              max={field.constraints?.max}
              onChange={e => handleChange(field.key, parseFloat(e.target.value) || 0)}
            />
          </div>
        )

      case 'string':
        return (
          <div className="modal-field" key={field.key}>
            <label className="modal-field-label">{field.label}</label>
            <input
              type="text"
              className="input"
              value={val ?? field.defaultValue ?? ''}
              onChange={e => handleChange(field.key, e.target.value)}
              placeholder={`Enter ${field.label.toLowerCase()}...`}
            />
          </div>
        )

      case 'select':
        return (
          <div className="modal-field" key={field.key}>
            <label className="modal-field-label">{field.label}</label>
            <select
              className="select"
              value={val ?? field.defaultValue ?? ''}
              onChange={e => handleChange(field.key, e.target.value)}
            >
              {(field.constraints?.options || []).map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        )

      case 'channelPicker':
        return (
          <div className="modal-field" key={field.key}>
            <label className="modal-field-label">{field.label}</label>
            <select
              className="select"
              value={val ?? ''}
              onChange={e => handleChange(field.key, e.target.value)}
            >
              <option value="">None</option>
              {channels
                .filter(c => c.type === 0 || c.type === 5)
                .map(c => (
                  <option key={c.id} value={c.id}>#{c.name}</option>
                ))}
            </select>
          </div>
        )

      case 'rolePicker':
        return (
          <div className="modal-field" key={field.key}>
            <label className="modal-field-label">{field.label}</label>
            <select
              className="select"
              value={val ?? ''}
              onChange={e => handleChange(field.key, e.target.value)}
            >
              <option value="">None</option>
              {roles.map(r => (
                <option key={r.id} value={r.id}>@{r.name}</option>
              ))}
            </select>
          </div>
        )

      case 'duration':
        return (
          <div className="modal-field" key={field.key}>
            <label className="modal-field-label">{field.label}</label>
            <input
              type="number"
              className="input"
              value={val ?? field.defaultValue ?? ''}
              min={field.constraints?.min}
              max={field.constraints?.max}
              onChange={e => handleChange(field.key, parseInt(e.target.value) || 0)}
            />
            <span className="modal-field-desc">Duration in seconds</span>
          </div>
        )

      case 'stringList':
        return (
          <div className="modal-field" key={field.key}>
            <label className="modal-field-label">{field.label}</label>
            <input
              type="text"
              className="input"
              value={Array.isArray(val) ? val.join(', ') : (val ?? '')}
              onChange={e => handleChange(field.key, e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
              placeholder="Comma-separated values..."
            />
          </div>
        )

      default:
        return (
          <div className="modal-field" key={field.key}>
            <label className="modal-field-label">{field.label}</label>
            <input
              type="text"
              className="input"
              value={val ?? ''}
              onChange={e => handleChange(field.key, e.target.value)}
            />
          </div>
        )
    }
  }

  const hasSchema = schema.length > 0

  return (
    <div className="modal-overlay" data-position="right" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title">
            <div style={{ 
              width: 36, height: 36,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: 'var(--radius-md)',
              background: `${module.color}15`, color: module.color 
            }}>
              <module.icon size={18} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{module.name}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{module.category}</div>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {loadingPickers ? (
            <div className="empty-state" style={{ padding: '40px 0' }}>
              <Loader2 size={24} className="spin" />
              <p>Loading settings...</p>
            </div>
          ) : hasSchema ? (
            Object.entries(sections).map(([sectionName, fields]) => (
              <div className="modal-section" key={sectionName}>
                <div className="modal-section-title">{sectionName}</div>
                {fields.map(field => renderField(field))}
              </div>
            ))
          ) : (
            <div className="empty-state" style={{ padding: '40px 0' }}>
              <SlidersHorizontal size={32} />
              <h3>No settings available</h3>
              <p>This module doesn't have configurable settings yet.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {hasSchema && (
          <div className="modal-footer">
            <button className="btn btn-ghost btn-sm" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
              Save Changes
            </button>
          </div>
        )}
      </div>

      {toast && (
        <div className="toast-container">
          <div className={`toast toast-${toast.type}`}>
            {toast.type === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
            {toast.message}
          </div>
        </div>
      )}
    </div>
  )
}
