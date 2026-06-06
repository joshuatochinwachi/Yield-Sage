"use client";

import { MouseGradientBackground } from "@/components/mouse-gradient-background";
import Link from "next/link";
import { Cookie, ArrowLeft, BarChart2 } from "lucide-react";

export default function CookiesPage() {
  return (
    <div className="min-h-screen relative overflow-hidden bg-[#050505] text-white" style={{ fontFamily: "var(--font-sans, Inter, sans-serif)" }}>
      <MouseGradientBackground />

      {/* Header */}
      <header className="sticky top-0 z-40 w-full border-b border-white/5 bg-black/60 backdrop-blur-xl">
        <div className="flex items-center justify-between w-full max-w-[1200px] mx-auto px-6 py-4">
          <Link href="/" className="flex items-center gap-2.5 group">
            <img src="/logo.jpg" alt="YieldSage" className="w-7 h-7 rounded-lg border border-white/10 object-cover group-hover:border-[#00ff88]/50 transition-all" />
            <span className="font-sans font-light tracking-wider text-xs text-white/90 group-hover:text-white transition-colors">
              YIELD<span className="text-[#00ff88] font-medium font-mono">SAGE</span>
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-xs font-mono px-3 py-1.5 rounded-lg text-[#00ff88] border border-[#00ff88]/20 bg-[#00ff88]/07 hover:bg-[#00ff88]/14 transition-all flex items-center gap-1.5">
              <BarChart2 className="w-3 h-3" />
              Dashboard
            </Link>
            <Link href="/" className="text-xs font-mono text-white/40 hover:text-white flex items-center gap-1 transition-colors">
              <ArrowLeft className="w-3.5 h-3.5" /> Home
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 w-full max-w-[800px] mx-auto px-6 py-16 md:py-24 space-y-12">
        
        {/* Title */}
        <div className="space-y-4 text-center md:text-left">
          <div className="w-12 h-12 rounded-2xl bg-[#00ff88]/10 border border-[#00ff88]/20 flex items-center justify-center text-[#00ff88] mb-4 mx-auto md:mx-0 shadow-[0_0_20px_rgba(0,255,136,0.1)]">
            <Cookie className="w-6 h-6 animate-pulse" />
          </div>
          <h1 className="text-3xl md:text-5xl font-light tracking-tight">Cookie & Storage Policy</h1>
          <p className="text-xs font-mono text-white/45">Last Updated: June 6, 2026 · Version 1.0.0</p>
        </div>

        {/* Intro Card */}
        <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-xl space-y-4">
          <p className="text-sm leading-relaxed text-white/70">
            YieldSage does not use tracking cookies, targeting pixels, or cross-site analytics identifiers to log your private behaviors. 
          </p>
          <p className="text-sm leading-relaxed text-white/70">
            We use browser <strong className="text-white">Local Storage</strong> and essential session cookies strictly to enable core features like watchlist syncs, dashboard layouts, and theme configurations. This data remains on your local machine and is never shared with us.
          </p>
        </div>

        {/* Sections */}
        <div className="space-y-10 text-sm leading-relaxed text-white/60">
          
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">1. What is Browser Local Storage?</h2>
            <p>
              Local storage is a built-in feature of modern web browsers that allows websites to store key-value data locally on your computer or mobile device. Unlike standard tracking cookies, local storage data is not transmitted to backend servers automatically on every request. It resides strictly inside your browser, ensuring a higher level of user-controlled privacy.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">2. How YieldSage Uses Storage Mechanisms</h2>
            <p>
              We utilize browser storage for the following essential functionalities:
            </p>
            <table className="w-full text-left border-collapse mt-4">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="py-2 pr-4 text-xs font-semibold text-white">Storage Key / Type</th>
                  <th className="py-2 pr-4 text-xs font-semibold text-white">Purpose</th>
                  <th className="py-2 text-xs font-semibold text-white">Retention</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 font-mono text-[11px]">
                <tr>
                  <td className="py-3 pr-4 text-[#00ff88]">`yieldsage_watchlist`</td>
                  <td className="py-3 pr-4 text-white/60">Persists the pool UUIDs you star in the leaderboard.</td>
                  <td className="py-3 text-white/40">Persistent (Local)</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 text-[#00ff88]">`yieldsage_storage_consent`</td>
                  <td className="py-3 pr-4 text-white/60">Remembers your consent preference for storing local configs.</td>
                  <td className="py-3 text-white/40">Persistent (Local)</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 text-[#00ff88]">`sb-access-token` / `sb-refresh-token`</td>
                  <td className="py-3 pr-4 text-white/60">Enables secure login sessions via Supabase Auth.</td>
                  <td className="py-3 text-white/40">Session / Temporary</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">3. Third-Party Storage</h2>
            <p>
              When you interact with the on-chain features of the site using your Web3 wallets (e.g. MetaMask, WalletConnect, or Coinbase Wallet), those wallet extensions may independently store session credentials or transaction state values in local storage or cookies. This storage is governed by the privacy policies of your respective wallet software.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">4. How to Manage Local Storage</h2>
            <p>
              You can audit and delete local storage entries at any time using your browser settings:
            </p>
            <ul className="list-disc pl-5 space-y-2">
              <li>In Chrome or Brave: `Settings` → `Privacy and security` → `Site settings` → `View permissions and data stored across sites`.</li>
              <li>In Firefox: `Settings` → `Privacy & Security` → `Cookies and Site Data` → `Manage Data`.</li>
              <li>You can also click **Essentials Only** on our storage banner to decline watchlist caching.</li>
            </ul>
          </section>

        </div>

        {/* Back Link */}
        <div className="pt-6 border-t border-white/5">
          <Link href="/" className="text-xs font-mono text-white/40 hover:text-white flex items-center gap-1.5 transition-colors">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Homepage
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-black/40 py-8 text-center text-xs font-mono text-white/20 relative z-10">
        <div className="max-w-[1200px] mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <span>YieldSage Cookie Policy · v1.0.0</span>
          <div className="flex gap-4">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
