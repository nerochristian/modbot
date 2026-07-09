import type { Metadata } from 'next'
import { MembersClient } from '@/components/dashboard/members-client'

export const metadata: Metadata = { title: 'Members' }

export default function MembersPage() {
  return <MembersClient />
}
