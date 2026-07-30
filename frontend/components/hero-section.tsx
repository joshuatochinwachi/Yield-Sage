"use client"

import { motion } from "framer-motion"

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex flex-col" style={{ background: "#050505" }}>
      {/* Nav */}
      <header className="flex items-center justify-between px-6 md:px-12 py-6 relative z-20">
        <div className="flex items-center gap-2.5">
          <div
            className="w-5 h-5 rounded-full"
            style={{
              background: "radial-gradient(circle, rgba(0,255,136,0.9) 0%, rgba(0,255,136,0.3) 100%)",
              boxShadow: "0 0 12px rgba(0,255,136,0.5)",
            }}
          />
          <span className="text-sm font-semibold tracking-tight text-white/90">YieldSage</span>
        </div>

        <nav className="hidden md:flex items-center gap-8">
          {["Protocol", "Intelligence", "Allocation", "Docs"].map((item) => (
            <a
              key={item}
              href={`#${item.toLowerCase()}`}
              className="text-xs text-white/40 hover:text-white/80 transition-colors tracking-wide"
            >
              {item}
            </a>
          ))}
        </nav>

        <a
          href="#agent"
          className="flex items-center gap-2 text-[11px] font-medium tracking-wide px-4 py-2 rounded-full border transition-all"
          style={{
            borderColor: "rgba(0,255,136,0.3)",
            color: "rgba(0,255,136,0.9)",
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLAnchorElement
            el.style.background = "rgba(0,255,136,0.08)"
            el.style.borderColor = "rgba(0,255,136,0.6)"
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLAnchorElement
            el.style.background = "transparent"
            el.style.borderColor = "rgba(0,255,136,0.3)"
          }}
        >
          <span
            style={{
              display: "inline-block",
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "rgba(0,255,136,1)",
              boxShadow: "0 0 6px rgba(0,255,136,0.9)",
              animation: "ping 1.5s ease-in-out infinite",
            }}
          />
          Launch AI Agent
        </a>
      </header>

      {/* Hero body */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center pb-24">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-10"
          style={{
            border: "1px solid rgba(0,255,136,0.15)",
            background: "rgba(0,255,136,0.04)",
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: "rgba(0,255,136,1)",
              boxShadow: "0 0 6px rgba(0,255,136,0.8)",
              animation: "ping 1.5s ease-in-out infinite",
            }}
          />
          <span className="text-[10px] tracking-[0.3em] text-white/40 uppercase font-mono">
            Live on Solana Network
          </span>
        </motion.div>

        {/* Main headline */}
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
          className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-semibold tracking-tight leading-none max-w-4xl"
          style={{ color: "rgba(255,255,255,0.92)" }}
        >
          The Yield Intelligence
          <br />
          <span style={{ color: "rgba(255,255,255,0.4)" }}>Layer for Solana.</span>
        </motion.h1>

        {/* Sub copy */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="mt-8 text-sm md:text-base leading-relaxed max-w-md"
          style={{ color: "rgba(255,255,255,0.38)" }}
        >
          AI-powered. On-chain verifiable. Risk-adjusted.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-col sm:flex-row items-center gap-3 mt-12"
        >
          <a
            id="access"
            href="#agent"
            className="px-7 py-3 rounded-full text-sm font-medium tracking-wide transition-all"
            style={{
              background: "rgba(0,255,136,1)",
              color: "#050505",
              boxShadow: "0 0 30px rgba(0,255,136,0.25)",
            }}
          >
            Get Early Access
          </a>
          <a
            href="#sequence"
            className="px-7 py-3 rounded-full text-sm font-medium tracking-wide transition-all"
            style={{
              border: "1px solid rgba(255,255,255,0.1)",
              color: "rgba(255,255,255,0.55)",
            }}
          >
            Explore Protocol ↓
          </a>
        </motion.div>

        {/* Scroll cue */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.2 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        >
          <span className="text-[9px] tracking-[0.45em] font-mono uppercase" style={{ color: "rgba(255,255,255,0.2)" }}>
            Scroll to explore
          </span>
          <div className="relative mt-2">
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="rgba(0,255,136,0.5)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="animate-bounce"
              style={{ animationDuration: "2s" }}
            >
              <path d="M12 5v14M19 12l-7 7-7-7" />
            </svg>
          </div>
        </motion.div>
      </div>

      {/* Bottom blend into sequence */}
      <div
        className="absolute bottom-0 inset-x-0 h-48 pointer-events-none"
        style={{ background: "linear-gradient(to bottom, transparent 0%, #050505 100%)" }}
      />
    </section>
  )
}
