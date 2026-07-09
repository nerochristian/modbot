import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/session'
import { BillingClient } from '@/components/dashboard/billing-client'

export const metadata: Metadata = { title: 'Billing' }

export default async function BillingPage() {
  const user = await getCurrentUser()
  if (!user) redirect('/login')
  if (!user.permissions.includes('billing.read')) redirect('/dashboard')
  return <BillingClient />
}
