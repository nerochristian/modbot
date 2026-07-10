import type { Metadata } from 'next'
import { AuthForm } from '@/components/auth/auth-form'

export const metadata: Metadata = { title: 'Sign in' }

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>
}) {
  const { next, error } = await searchParams
  const target = next?.startsWith('/') && !next.startsWith('//') ? next : '/servers'
  return <AuthForm mode="login" next={target} error={error} />
}
