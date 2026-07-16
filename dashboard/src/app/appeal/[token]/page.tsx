import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { Logo } from '@/components/logo'
import { Card, CardContent } from '@/components/ui/card'
import { getAppealPortalCase } from '@/lib/appeal-portal-service'
import { AppealForm } from './appeal-form'

export const dynamic = 'force-dynamic'
export const metadata: Metadata = {
  title: 'Submit an appeal',
  robots: { index: false, follow: false },
}

export default async function AppealPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  const result = await getAppealPortalCase(token)
  if (result.kind === 'not_found') notFound()

  return (
    <main className="relative min-h-screen overflow-hidden bg-bg px-4 py-10 sm:py-16">
      <div className="grid-texture pointer-events-none absolute inset-0 opacity-30" />
      <div className="relative mx-auto w-full max-w-xl">
        <div className="mb-8 flex justify-center"><Logo /></div>
        {result.kind === 'ok' ? (
          <AppealForm token={token} moderationCase={result.case} questions={result.questions} />
        ) : (
          <Card>
            <CardContent className="py-10 text-center">
              <h1 className="font-display text-2xl font-semibold text-foreground">
                {result.kind === 'expired' ? 'Appeal link expired' : result.kind === 'closed' ? 'Appeals are closed' : 'Appeal already submitted'}
              </h1>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">
                {result.kind === 'expired'
                  ? 'This case can no longer be appealed with this link. Contact the server moderation team if you still need help.'
                  : result.kind === 'closed'
                    ? 'This server is not accepting new appeal submissions right now. Your link remains private and cannot be used while submissions are closed.'
                  : 'This one-time link has already been used. The moderation team has the submitted appeal.'}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  )
}
