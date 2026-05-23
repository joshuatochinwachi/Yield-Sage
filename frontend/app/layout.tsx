import type React from "react"
import type { Metadata, Viewport } from "next"
import { Inter, Cormorant_Garamond } from "next/font/google"
import { LenisProvider } from "@/components/lenis-provider"
import "./globals.css"

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" })
const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-serif",
})

export const metadata: Metadata = {
  title: "YieldSage | AI-Powered DeFi Yield Intelligence on Mantle",
  description:
    "Maximize your yield optimization with autonomous allocations, real-time risk-adjusted models, and secure on-chain intelligence. Built natively on Mantle Network.",
  icons: { icon: "/logo.jpg" },
  openGraph: {
    title: "YieldSage | AI-Powered DeFi Yield Intelligence on Mantle",
    description:
      "Autonomous yield optimization. Real-time on-chain intelligence. Built for Mantle.",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "YieldSage" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "YieldSage | AI-Powered DeFi Yield Intelligence on Mantle",
    description: "Autonomous yield optimization. Real-time on-chain intelligence. Built for Mantle.",
    images: ["/og-image.png"],
  },
}

export const viewport: Viewport = {
  themeColor: "#050505",
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${cormorant.variable}`} suppressHydrationWarning style={{ background: "#050505" }}>
      <head>
        <style dangerouslySetInnerHTML={{ __html: 'html,body{background:#050505!important}' }} />
      </head>
      <body
        className="font-sans antialiased"
        style={{ background: "#050505", color: "rgba(255,255,255,0.9)", overflowX: "hidden" }}
      >
        <LenisProvider>
          {children}
        </LenisProvider>
      </body>
    </html>
  )
}
