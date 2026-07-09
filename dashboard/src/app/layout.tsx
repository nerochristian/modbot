import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { ThemeScript } from '@/components/theme-script'
import { ToastProvider } from '@/components/ui/toast'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })

const appName = process.env.NEXT_PUBLIC_APP_NAME ?? 'Aegis'

export const metadata: Metadata = {
  title: {
    default: `${appName} — Moderation & safety for Discord communities`,
    template: `%s · ${appName}`,
  },
  description:
    'Aegis is a complete moderation platform for Discord servers: automod, cases, appeals, member intelligence, and a fully configurable command deck for your whole mod team.',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      data-density="compact"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
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
