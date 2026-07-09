import { z } from 'zod'
import { ROLES } from '@/lib/rbac'

export const registerSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(80),
  email: z.email('Enter a valid email').max(160),
  password: z.string().min(8, 'Password must be at least 8 characters').max(200),
})

export const loginSchema = z.object({
  email: z.email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

export const updateProfileSchema = z.object({
  name: z.string().min(2).max(80).optional(),
  title: z.string().max(120).nullable().optional(),
  phone: z.string().max(40).nullable().optional(),
  timezone: z.string().max(60).optional(),
  bio: z.string().max(500).nullable().optional(),
  avatarColor: z.string().regex(/^#[0-9a-fA-F]{6}$/).optional(),
})

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1),
    newPassword: z.string().min(8, 'Password must be at least 8 characters').max(200),
  })

export const createUserSchema = z.object({
  name: z.string().min(2).max(80),
  email: z.email(),
  role: z.enum(ROLES),
  password: z.string().min(8).max(200).optional(),
})

export const updateUserSchema = z.object({
  name: z.string().min(2).max(80).optional(),
  role: z.enum(ROLES).optional(),
  status: z.enum(['active', 'invited', 'suspended']).optional(),
  title: z.string().max(120).nullable().optional(),
})

export const memberSchema = z.object({
  username: z.string().min(2).max(80),
  displayName: z.string().min(1).max(80),
  discordId: z.string().regex(/^\d{15,20}$/, 'Enter a valid Discord ID (15–20 digits)'),
  standing: z.enum(['good', 'watchlist', 'muted', 'banned', 'left']),
  riskLevel: z.enum(['low', 'medium', 'high', 'critical']),
  note: z.string().max(500).nullable().optional(),
})

export const caseSchema = z.object({
  memberId: z.string().min(1, 'Select a member'),
  type: z.enum(['note', 'warn', 'mute', 'timeout', 'kick', 'ban', 'unban']),
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  reason: z.string().min(3, 'Give a reason').max(500),
  channel: z.string().max(80).nullable().optional(),
  durationHours: z.number().int().min(0).max(8760).nullable().optional(),
})

export const updateCaseSchema = z.object({
  status: z.enum(['open', 'resolved', 'expired', 'appealed']).optional(),
  severity: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  reason: z.string().min(3).max(500).optional(),
})

export const automodRuleSchema = z.object({
  name: z.string().min(2).max(80),
  description: z.string().max(300).nullable().optional(),
  trigger: z.enum([
    'keyword',
    'regex',
    'spam',
    'mention_spam',
    'invite',
    'link',
    'caps',
    'attachment',
  ]),
  pattern: z.string().max(500).nullable().optional(),
  action: z.enum(['delete', 'warn', 'mute', 'timeout', 'kick', 'ban', 'flag']),
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  exemptRoles: z.array(z.string().max(60)).max(30).optional(),
  enabled: z.boolean().optional(),
})

export const appealDecisionSchema = z.object({
  status: z.enum(['approved', 'denied']),
  decision: z.string().max(500).nullable().optional(),
})

export const reportSchema = z.object({
  name: z.string().min(2).max(120),
  type: z.enum(['actions', 'members', 'activity', 'automod', 'custom']),
  format: z.enum(['csv', 'json', 'pdf', 'xlsx']),
  params: z.record(z.string(), z.unknown()).optional(),
})

export const savedViewSchema = z.object({
  name: z.string().min(1).max(80),
  page: z.string().min(1).max(40),
  state: z.record(z.string(), z.unknown()),
})
