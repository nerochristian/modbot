'use client'

import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { LogOut, User, Settings, ShieldCheck } from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  DropdownLabel,
  DropdownSeparator,
} from '@/components/ui/dropdown'
import { Avatar } from '@/components/ui/avatar'
import { useConfigStore } from '@/lib/store'
import { ROLE_LABELS } from '@/lib/rbac'
import { useToast } from '@/components/ui/toast'

export function UserMenu() {
  const router = useRouter()
  const toast = useToast()
  const user = useConfigStore((s) => s.user)
  const can = useConfigStore((s) => s.can)
  if (!user) return null

  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => undefined)
    toast.success('Signed out')
    router.push('/login')
    router.refresh()
  }

  return (
    <Dropdown>
      <DropdownTrigger>
        <span className="focus-ring flex items-center gap-2 rounded-lg p-1 pr-2 transition-colors hover:bg-surface-2">
          <Avatar name={user.name} color={user.avatarColor} size="sm" />
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-medium leading-tight text-foreground">{user.name}</span>
            <span className="block text-xs leading-tight text-muted">{ROLE_LABELS[user.role]}</span>
          </span>
        </span>
      </DropdownTrigger>
      <DropdownMenu>
        <DropdownLabel>
          <span className="block truncate text-foreground">{user.name}</span>
          <span className="block truncate font-normal text-muted-2">{user.email}</span>
        </DropdownLabel>
        <DropdownSeparator />
        <Link href="/dashboard/settings/profile">
          <DropdownItem icon={User}>Profile</DropdownItem>
        </Link>
        <Link href="/dashboard/settings">
          <DropdownItem icon={Settings}>Settings</DropdownItem>
        </Link>
        {can('admin.access') && (
          <Link href="/dashboard/admin">
            <DropdownItem icon={ShieldCheck}>Admin panel</DropdownItem>
          </Link>
        )}
        <DropdownSeparator />
        <DropdownItem icon={LogOut} destructive onClick={logout}>
          Sign out
        </DropdownItem>
      </DropdownMenu>
    </Dropdown>
  )
}
