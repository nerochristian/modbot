import { prisma } from '@/lib/prisma'

/**
 * Lightweight append helpers for the activity feed, audit trail, and
 * notifications. Called from route handlers after successful mutations.
 */

export async function logActivity(params: {
  guildId?: string
  userId?: string | null
  actorName: string
  action: string
  target?: string | null
  metadata?: Record<string, unknown>
}): Promise<void> {
  await prisma.activityLog.create({
    data: {
      guildId: params.guildId ?? '',
      userId: params.userId ?? null,
      actorName: params.actorName,
      action: params.action,
      target: params.target ?? null,
      metadata: params.metadata ? JSON.stringify(params.metadata) : null,
    },
  })
}

export async function logAudit(params: {
  guildId?: string
  userId?: string | null
  actorName: string
  action: string
  entity: string
  entityId?: string | null
  ip?: string | null
  userAgent?: string | null
  metadata?: Record<string, unknown>
}): Promise<void> {
  await prisma.auditLog.create({
    data: {
      guildId: params.guildId ?? '',
      userId: params.userId ?? null,
      actorName: params.actorName,
      action: params.action,
      entity: params.entity,
      entityId: params.entityId ?? null,
      ip: params.ip ?? null,
      userAgent: params.userAgent ?? null,
      metadata: params.metadata ? JSON.stringify(params.metadata) : null,
    },
  })
}

export async function notify(params: {
  guildId?: string
  userId: string
  type?: string
  level?: string
  title: string
  body: string
  href?: string | null
}): Promise<void> {
  await prisma.notification.create({
    data: {
      guildId: params.guildId ?? '',
      userId: params.userId,
      type: params.type ?? 'system',
      level: params.level ?? 'info',
      title: params.title,
      body: params.body,
      href: params.href ?? null,
    },
  })
}
