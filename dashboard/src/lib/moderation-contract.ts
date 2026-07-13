export type ModerationAutopunishAction = 'timeout' | 'kick' | 'ban'

export type ModerationAutopunishRule = {
  warnings: number
  action: ModerationAutopunishAction
  durationMinutes: number | null
}

export const MAX_AUTOPUNISH_RULES = 20
export const MAX_TIMEOUT_MINUTES = 28 * 24 * 60

const ACTION_SEVERITY: Record<ModerationAutopunishAction, number> = {
  timeout: 0,
  kick: 1,
  ban: 2,
}

function integer(value: unknown): number | null {
  if (typeof value === 'number' && Number.isSafeInteger(value)) return value
  if (typeof value === 'string' && /^\d+$/.test(value.trim())) {
    const parsed = Number(value.trim())
    return Number.isSafeInteger(parsed) ? parsed : null
  }
  return null
}

export function parseModerationAutopunishRules(value: unknown): ModerationAutopunishRule[] {
  if (!Array.isArray(value)) throw new Error('Autopunish rules must be a list')
  if (value.length > MAX_AUTOPUNISH_RULES) {
    throw new Error(`Autopunish supports at most ${MAX_AUTOPUNISH_RULES} rules`)
  }

  const rules = value.map((entry, index): ModerationAutopunishRule => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      throw new Error(`Autopunish rule ${index + 1} must be an object`)
    }
    const raw = entry as Record<string, unknown>
    const unknownKeys = Object.keys(raw).filter((key) => (
      key !== 'warnings' && key !== 'action' && key !== 'durationMinutes'
    ))
    if (unknownKeys.length) throw new Error(`Autopunish rule ${index + 1} has unsupported fields`)

    const warnings = integer(raw.warnings)
    if (warnings === null || warnings < 1 || warnings > 100) {
      throw new Error(`Autopunish rule ${index + 1} warnings must be from 1 to 100`)
    }
    const action = raw.action === 'mute' ? 'timeout' : raw.action
    if (action !== 'timeout' && action !== 'kick' && action !== 'ban') {
      throw new Error(`Autopunish rule ${index + 1} has an invalid action`)
    }

    const duration = raw.durationMinutes === null || raw.durationMinutes === undefined
      ? null
      : integer(raw.durationMinutes)
    if (action === 'timeout') {
      if (duration === null || duration < 1 || duration > MAX_TIMEOUT_MINUTES) {
        throw new Error(`Autopunish timeout duration must be from 1 to ${MAX_TIMEOUT_MINUTES} minutes`)
      }
      return { warnings, action, durationMinutes: duration }
    }
    if (duration !== null && duration !== 0) {
      throw new Error(`Autopunish ${action} rules cannot include a duration`)
    }
    return { warnings, action, durationMinutes: null }
  }).sort((a, b) => a.warnings - b.warnings)

  if (new Set(rules.map((rule) => rule.warnings)).size !== rules.length) {
    throw new Error('Autopunish warning counts must be unique')
  }
  for (let index = 1; index < rules.length; index += 1) {
    if (ACTION_SEVERITY[rules[index].action] < ACTION_SEVERITY[rules[index - 1].action]) {
      throw new Error('Autopunish actions cannot become less severe at higher warning counts')
    }
  }
  return rules
}

export function moderationAutopunishRulesFromSettings(
  settings: Record<string, unknown>,
): ModerationAutopunishRule[] {
  if (settings.warn_thresholds_enabled === false) return []
  if (Object.prototype.hasOwnProperty.call(settings, 'moderation_autopunish_rules')) {
    try {
      return parseModerationAutopunishRules(settings.moderation_autopunish_rules)
    } catch {
      return []
    }
  }

  const timeoutAt = integer(settings.warn_threshold_mute ?? 3) ?? 3
  const kickAt = integer(settings.warn_threshold_kick ?? 5) ?? 5
  const banAt = integer(settings.warn_threshold_ban ?? 7) ?? 7
  const durationSeconds = integer(settings.warn_mute_duration ?? 3600) ?? 3600
  const legacy: ModerationAutopunishRule[] = []
  if (timeoutAt > 0) {
    legacy.push({
      warnings: timeoutAt,
      action: 'timeout',
      durationMinutes: Math.min(MAX_TIMEOUT_MINUTES, Math.max(1, Math.ceil(durationSeconds / 60))),
    })
  }
  if (kickAt > 0) legacy.push({ warnings: kickAt, action: 'kick', durationMinutes: null })
  if (banAt > 0) legacy.push({ warnings: banAt, action: 'ban', durationMinutes: null })
  try {
    return parseModerationAutopunishRules(legacy)
  } catch {
    return []
  }
}

export function legacyThresholdSnapshot(rules: ModerationAutopunishRule[]): Record<string, unknown> {
  const timeout = rules.find((rule) => rule.action === 'timeout')
  const kick = rules.find((rule) => rule.action === 'kick')
  const ban = rules.find((rule) => rule.action === 'ban')
  return {
    warn_thresholds_enabled: rules.length > 0,
    warn_threshold_mute: timeout?.warnings ?? 0,
    warn_mute_duration: timeout?.durationMinutes ? timeout.durationMinutes * 60 : 3600,
    warn_threshold_kick: kick?.warnings ?? 0,
    warn_threshold_ban: ban?.warnings ?? 0,
  }
}
