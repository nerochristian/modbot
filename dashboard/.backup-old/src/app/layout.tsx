import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { ThemeScript } from '@/components/theme-script'
import { ToastProvider } from '@/components/ui/toast'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })

const appName = process.env.NEXT_PUBLIC_APP_NAME ?? 'Nebula'

export const metadata: Metadata = {
  title: {
    default: `${appName} — Analytics & operations for modern SaaS`,
    template: `%s · ${appName}`,
  },
  description:
    'Nebula is a complete analytics and operations platform: revenue, customers, retention, and a fully configurable dashboard for your whole team.',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      data-density="comfortable"
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
