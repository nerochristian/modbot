import type { Metadata } from 'next'
import { UsersClient } from '@/components/dashboard/users-client'

export const metadata: Metadata = { title: 'Users' }

export default function UsersPage() {
  return <UsersClient />
}
