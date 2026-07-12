import type { Metadata } from 'next'
import { Space_Grotesk, IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google'
import './globals.css'
import { ThemeScript } from '@/components/theme-script'
import { ToastProvider } from '@/components/ui/toast'

// Display: Space Grotesk — instrument-panel titles and figures.
const displayFont = Space_Grotesk({
  variable: '--font-display',
  subsets: ['latin'],
  weight: ['500', '600', '700'],
})
// Body / UI: IBM Plex Sans — institutional voice that holds up in dense tables.
const sansFont = IBM_Plex_Sans({
  variable: '--font-sans-custom',
  subsets: ['latin'],
  weight: ['400', '500', '600'],
})
// Data: IBM Plex Mono — case IDs, Discord IDs, timestamps; carries the stamp signature.
const monoFont = IBM_Plex_Mono({
  variable: '--font-mono-custom',
  subsets: ['latin'],
  weight: ['400', '500', '600'],
})

const appName = process.env.NEXT_PUBLIC_APP_NAME ?? 'Docket'

export const metadata: Metadata = {
  title: {
    default: `${appName} — The moderation caseload for Discord communities`,
    template: `%s · ${appName}`,
  },
  description:
    'Docket is a moderation records desk for Discord servers: automod, cases, appeals, member intelligence, and a fully configurable console for your whole mod team. Work your caseload.',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      data-density="compact"
      className={`${displayFont.variable} ${sansFont.variable} ${monoFont.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <ThemeScript />
      </head>
      <body className="min-h-full">
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  )
}
