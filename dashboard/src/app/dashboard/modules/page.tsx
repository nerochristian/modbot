import type { Metadata } from 'next'
import { ModulesClient } from '@/components/dashboard/modules-client'

export const metadata: Metadata = { title: 'Modules' }

export default function ModulesPage() {
  return <ModulesClient />
}
