import type { Metadata } from 'next'
import { Suspense } from 'react'
import { Sora, DM_Sans } from 'next/font/google'
import PostHogProvider from '@/components/PostHogProvider'
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
  title: 'SheetMind — AI Sidebar for Google Sheets | Chat, Act, Undo',
  description:
    'Chat with your Google Sheets data using AI. SheetMind understands your spreadsheet, writes validated formulas, takes actions, and lets you undo every change.',
  openGraph: {
    title: 'SheetMind: The AI Copilot for Google Sheets That Lets You Undo',
    description:
      'Ask questions about your data in plain English. Get formulas, formatting, and analysis — with step-by-step undo for every AI action. Privacy-first. Free to start.',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'SheetMind — Ask anything. Change anything. Undo anything.',
    description:
      'The AI sidebar for Google Sheets. Validated formulas. PII detection. Step-by-step undo. Free to start.',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${sora.variable} ${dmSans.variable}`}>
      <body className="font-body antialiased">
        <Suspense fallback={null}>
          <PostHogProvider>{children}</PostHogProvider>
        </Suspense>
      </body>
    </html>
  )
}
