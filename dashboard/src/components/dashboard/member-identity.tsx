'use client'

import { Avatar } from '@/components/ui/avatar'
import { useToast } from '@/components/ui/toast'
import { cn } from '@/lib/utils'

export type MemberIdentityData = {
  id: string
  discordId?: string
  username: string
  displayName: string
  nickname?: string | null
  avatarUrl?: string | null
  avatarColor?: string
}

/**
 * Discord identity chip: real avatar, nickname/display name + @username.
 * Hovering swaps the second line to the user ID; clicking copies it.
 */
export function MemberIdentity({
  member,
  size = 'sm',
  copyable = true,
  className,
}: {
  member: MemberIdentityData
  size?: 'xs' | 'sm' | 'md' | 'lg'
  copyable?: boolean
  className?: string
}) {
  const toast = useToast()
  const discordId = member.discordId ?? member.id
  const primary = member.nickname || member.displayName
  const secondary = `@${member.username}`

  async function copyId(event: React.MouseEvent) {
    if (!copyable) return
    event.stopPropagation()
    try {
      await navigator.clipboard.writeText(discordId)
      toast.success('User ID copied to clipboard')
    } catch {
      toast.error('Could not copy the user ID')
    }
  }

  return (
    <button
      type="button"
      onClick={copyId}
      title={copyable ? `Copy user ID ${discordId}` : undefined}
      className={cn(
        'group/member flex min-w-0 items-center gap-3 rounded-md text-left',
        copyable && 'cursor-copy',
        className,
      )}
    >
      <Avatar name={primary} color={member.avatarColor} src={member.avatarUrl} size={size} />
      <span className="min-w-0">
        <span className="block truncate font-medium text-foreground">{primary}</span>
        <span className="relative block h-4 truncate text-xs">
          <span className="absolute inset-0 text-muted transition-opacity duration-150 group-hover/member:opacity-0">
            {secondary}
          </span>
          <span className="mono-id absolute inset-0 text-accent opacity-0 transition-opacity duration-150 group-hover/member:opacity-100">
            {discordId}
          </span>
        </span>
      </span>
    </button>
  )
}
