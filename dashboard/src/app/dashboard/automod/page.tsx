import type { Metadata } from 'next'
import { AutomodClient } from '@/components/dashboard/automod-client'

export const metadata: Metadata = { title: 'Automod' }

export default function AutomodPage() {
  return <AutomodClient />
}
