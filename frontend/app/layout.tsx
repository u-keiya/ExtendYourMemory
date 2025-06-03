import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Extend Your Memory',
  description: 'AI-powered search and report generation from your digital memory',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  )
}