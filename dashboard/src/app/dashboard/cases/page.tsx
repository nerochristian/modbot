import type { Metadata } from 'next'
import { CasesClient } from '@/components/dashboard/cases-client'

export const metadata: Metadata = { title: 'Cases' }

export default function CasesPage() {
  return <CasesClient />
}
