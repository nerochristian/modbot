import type { Metadata } from 'next'
import { MemberReportsClient } from '@/components/dashboard/member-reports-client'

export const metadata: Metadata = { title: 'Reports' }

export default function ReportsPage() {
  return <MemberReportsClient />
}
