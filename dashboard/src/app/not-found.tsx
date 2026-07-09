import Link from 'next/link'
import { Logo } from '@/components/logo'
import { buttonVariants } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <Logo size="lg" />
      <p className="mt-8 text-7xl font-bold tracking-tight text-accent">404</p>
      <h1 className="mt-4 text-2xl font-bold tracking-tight text-foreground">Page not found</h1>
      <p className="mt-2 max-w-md text-muted">
        The page you’re looking for doesn’t exist or may have been moved.
      </p>
      <div className="mt-8 flex gap-3">
        <Link href="/" className={buttonVariants({ variant: 'outline' })}>
          Back home
        </Link>
        <Link href="/dashboard" className={buttonVariants({ variant: 'primary' })}>
          Go to dashboard
        </Link>
      </div>
    </div>
  )
}
