"use client";

import { MouseGradientBackground } from "@/components/mouse-gradient-background";
import Link from "next/link";
import { Shield, ArrowLeft, BarChart2 } from "lucide-react";

export default function PrivacyPage() {
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
            <Shield className="w-6 h-6 animate-pulse" />
          </div>
          <h1 className="text-3xl md:text-5xl font-light tracking-tight">Privacy Policy</h1>
          <p className="text-xs font-mono text-white/45">Last Updated: June 6, 2026 · Version 1.0.0</p>
        </div>

        {/* Intro Card */}
        <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-xl space-y-4">
          <p className="text-sm leading-relaxed text-white/70">
            At <strong className="text-white">YieldSage</strong>, we are committed to security, transparency, and data minimization. Because YieldSage is a non-custodial intelligence platform, <strong className="text-white">we do not collect, store, or transmit your personal identifier details</strong> (such as name, physical address, or credit card information). 
          </p>
          <p className="text-sm leading-relaxed text-white/70">
            This policy outlines how the application utilizes Web3 signatures and public blockchain transactions to deliver customized yield notifications while keeping your privacy fully intact.
          </p>
        </div>

        {/* Sections */}
        <div className="space-y-10 text-sm leading-relaxed text-white/60">
          
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">1. Information We Collect (And What We Do Not)</h2>
            <p>
              We operate under a strict principle of data minimization:
            </p>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong className="text-white">Personal Data:</strong> We do not collect names, emails, IP addresses, or location data. 
              </li>
              <li>
                <strong className="text-white">Public Wallet Addresses:</strong> To manage simulated paper trades and alerts, we store public wallet addresses. Public addresses are entirely open and viewable on the Solana blockchain ledger. We never request private keys or seed phrases.
              </li>
              <li>
                <strong className="text-white">Telegram Integration Data:</strong> When using the YieldSage Bot, we securely store your Telegram numeric User ID and usernames to direct your customized hourly recommendations and watchlist status alerts.
              </li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">2. How We Use Information</h2>
            <p>
              Your public addresses and preferences are utilized solely for:
            </p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Calculating and displaying simulated paper trading P&L values on your dashboard.</li>
              <li>Routing hourly yield delta alerts and rebalancing recommendations to your designated Telegram chat.</li>
              <li>Persisting your custom pool watchlist to your local browser storage.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">3. Third-Party Services & Analytics</h2>
            <p>
              YieldSage interacts with high-grade external partners to stream data and compute recommendations:
            </p>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong className="text-white">Supabase / PostgreSQL:</strong> Stores protocol feeds, user preference states, and Telegram message queues. All database interactions utilize Row-Level Security (RLS) policies.
              </li>
              <li>
                <strong className="text-white">DefiLlama:</strong> Pulls public, aggregated DeFi statistics (TVL, APY) for Solana protocols. No user identity details are ever shared with DefiLlama.
              </li>
              <li>
                <strong className="text-white">AI Inference Networks:</strong> Sends public yield feeds to Cerebras, SambaNova, Groq, NVIDIA, and Gemini. Queries are completely anonymized before transmission.
              </li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">4. On-Chain Commitments</h2>
            <p>
              Every AI pick is hashed and written to the Solana blockchain as an SPL Memo transaction. This transaction remains visible in the global public ledger permanently. Do not link personal identifying descriptions to public addresses used on the site.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">5. Security of Information</h2>
            <p>
              Our database is secured with service role barriers, JWT auth handshakes, and strict RLS rules. However, please remember that you are responsible for securing your own Telegram accounts, wallets, and API configurations.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">6. Changes to this Policy</h2>
            <p>
              We reserve the right to modify this Privacy Policy. Any updates will be published on this page and reflected in the version history at the top of the document.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-white tracking-wide">7. Contact</h2>
            <p>
              For privacy audits, technical queries, or support requests, please contact us at <a href="mailto:yieldsageai@gmail.com" className="text-[#00ff88] hover:underline">yieldsageai@gmail.com</a> or reach out via the Telegram bot at <a href="https://t.me/YieldSageBot" className="text-[#00ff88] hover:underline">t.me/YieldSageBot</a>.
            </p>
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
          <span>YieldSage Privacy Policy · v1.0.0</span>
          <div className="flex gap-4">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
            <Link href="/cookies" className="hover:text-white transition-colors">Cookie Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
