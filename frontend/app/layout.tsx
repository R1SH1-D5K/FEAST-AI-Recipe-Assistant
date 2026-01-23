import type React from "react"
import type { Metadata, Viewport } from "next"
import { Outfit, Playfair_Display } from "next/font/google"
import "./globals.css"

const outfit = Outfit({ subsets: ["latin"], variable: "--font-sans" })
const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-heading" })

export const metadata: Metadata = {
  title: "Feast - AI Recipe Assistant",
  description: "Your intelligent cooking companion. Discover delicious recipes with AI-powered recommendations.",
    generator: 'v0.app'
}

export const viewport: Viewport = {
  themeColor: "#050608",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`${outfit.variable} ${playfair.variable} font-sans antialiased`}>{children}</body>
    </html>
  )
}
