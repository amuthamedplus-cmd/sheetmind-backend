import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Log In — SheetMind',
  description: 'Log in to your SheetMind account.',
}

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children
}
