import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { ThemeScript } from '@/components/theme-script'
import { ToastProvider } from '@/components/ui/toast'

// Body / UI: Inter — clean, legible, holds up in dense tables.
const sansFont = Inter({
  variable: '--font-sans-custom',
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
})
// Data: JetBrains Mono — case IDs, Discord IDs, timestamps, command surfaces.
const monoFont = JetBrains_Mono({
  variable: '--font-mono-custom',
  subsets: ['latin'],
  weight: ['400', '500', '600'],
})
// Display: Clash Display — loaded via Fontshare <link> below (not on next/font).

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
      className={`${sansFont.variable} ${monoFont.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Clash Display — premium geometric display face (Fontshare). */}
        <link
          href="https://api.fontshare.com/v2/css?f[]=clash-display@500,600,700&display=swap"
          rel="stylesheet"
        />
        <ThemeScript />
      </head>
      <body className="min-h-full">
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  )
}
