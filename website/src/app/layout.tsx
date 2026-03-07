import type { Metadata } from 'next'
import { Suspense } from 'react'
import { Sora, DM_Sans } from 'next/font/google'
import PostHogProvider from '@/components/PostHogProvider'
import JsonLd from '@/components/JsonLd'
import './globals.css'

const sora = Sora({
  subsets: ['latin'],
  variable: '--font-sora',
  display: 'swap',
  weight: ['400', '500', '600', '700', '800'],
})

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-dm-sans',
  display: 'swap',
  weight: ['400', '500', '600', '700'],
})

export const metadata: Metadata = {
  metadataBase: new URL('https://sheetmind.xyz'),
  title: 'SheetMind — AI Sidebar for Google Sheets | Chat, Act, Undo',
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    apple: [{ url: '/apple-touch-icon.png', sizes: '180x180' }],
    shortcut: '/favicon.ico',
  },
  manifest: '/site.webmanifest',
  description:
    'Chat with your Google Sheets data using AI. SheetMind understands your spreadsheet, writes validated formulas, takes actions, and lets you undo every change.',
  alternates: {
    canonical: '/',
  },
  openGraph: {
    title: 'SheetMind: The AI Copilot for Google Sheets That Lets You Undo',
    description:
      'Ask questions about your data in plain English. Get formulas, formatting, and analysis — with step-by-step undo for every AI action. Privacy-first. Free to start.',
    type: 'website',
    url: 'https://sheetmind.xyz',
    siteName: 'SheetMind',
    locale: 'en_US',
    images: [
      {
        url: '/og-default.png',
        width: 1200,
        height: 630,
        alt: 'SheetMind — AI Sidebar for Google Sheets',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@sheetmind',
    title: 'SheetMind — Ask anything. Change anything. Undo anything.',
    description:
      'The AI sidebar for Google Sheets. Validated formulas. PII detection. Step-by-step undo. Free to start.',
    images: ['/og-default.png'],
  },
}

const organizationSchema = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'SheetMind',
  url: 'https://sheetmind.xyz',
  logo: 'https://sheetmind.xyz/logo.png',
  description:
    'AI sidebar for Google Sheets that reads your data, takes action, and lets you undo every step.',
  sameAs: [],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${sora.variable} ${dmSans.variable} overflow-x-hidden`}>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://us.i.posthog.com" />
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/favicon-32x32.png" type="image/png" sizes="32x32" />
        <link rel="icon" href="/favicon-16x16.png" type="image/png" sizes="16x16" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/site.webmanifest" />
        <meta name="theme-color" content="#10b981" />
        <JsonLd data={organizationSchema} />
      </head>
      <body className="font-body antialiased overflow-x-hidden">
        <Suspense fallback={null}>
          <PostHogProvider>{children}</PostHogProvider>
        </Suspense>
      </body>
    </html>
  )
}
