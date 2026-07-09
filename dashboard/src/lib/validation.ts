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

export const customerSchema = z.object({
  name: z.string().min(2).max(120),
  email: z.email(),
  company: z.string().max(120).nullable().optional(),
  plan: z.enum(['free', 'starter', 'pro', 'enterprise']),
  status: z.enum(['active', 'trialing', 'past_due', 'churned']),
  country: z.string().max(2),
  mrr: z.number().int().min(0).optional(),
})

export const reportSchema = z.object({
  name: z.string().min(2).max(120),
  type: z.enum(['revenue', 'users', 'activity', 'retention', 'custom']),
  format: z.enum(['csv', 'json', 'pdf', 'xlsx']),
  params: z.record(z.string(), z.unknown()).optional(),
})

export const savedViewSchema = z.object({
  name: z.string().min(1).max(80),
  page: z.string().min(1).max(40),
  state: z.record(z.string(), z.unknown()),
})
