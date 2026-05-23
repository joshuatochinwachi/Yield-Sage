"use client"

import { useRef } from "react"
import { motion, useInView } from "framer-motion"

export function Footer() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-60px" })

  return (
    <footer
      id="access"
      className="relative px-6 md:px-12 pt-28 md:pt-40 pb-14"
      style={{ background: "transparent" }}
    >
      {/* Top border line */}
      <div
        className="absolute top-0 inset-x-0 h-px"
        style={{
          background:
            "linear-gradient(to right, transparent 0%, rgba(255,255,255,0.06) 30%, rgba(0,255,136,0.15) 50%, rgba(255,255,255,0.06) 70%, transparent 100%)",
        }}
      />

      {/* Ambient glow */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-64 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at 50% 0%, rgba(0,255,136,0.06) 0%, transparent 70%)",
        }}
      />

      <div ref={ref} className="max-w-5xl mx-auto relative z-10">
        <div className="flex flex-col items-center text-center mb-24 md:mb-32">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.85, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="text-3xl md:text-5xl lg:text-6xl font-semibold tracking-tight leading-tight mb-12"
            style={{ color: "rgba(255,255,255,0.9)" }}
          >
            Start Finding Alpha
            <br />
            <span style={{ color: "rgba(255,255,255,0.3)" }}>on Mantle.</span>
          </motion.h2>

          {/* Launch App CTA */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            <a
              href="#"
              className="inline-block px-10 py-4 rounded-full text-sm font-medium tracking-wide transition-all"
              style={{
                background: "rgba(0,255,136,1)",
                color: "#050505",
                boxShadow: "0 0 24px rgba(0,255,136,0.25)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = "0 0 40px rgba(0,255,136,0.4)"
                e.currentTarget.style.transform = "translateY(-1px)"
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = "0 0 24px rgba(0,255,136,0.25)"
                e.currentTarget.style.transform = "translateY(0)"
              }}
            >
              Launch App
            </a>
          </motion.div>
        </div>

        {/* Bottom footer row */}
        <div
          className="flex flex-col md:flex-row items-center justify-between gap-6 pt-8"
          style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
        >
          {/* Logo + caption */}
          <div className="flex items-center gap-2.5">
            <div
              className="w-4 h-4 rounded-full"
              style={{
                background:
                  "radial-gradient(circle, rgba(0,255,136,0.9) 0%, rgba(0,255,136,0.3) 100%)",
                boxShadow: "0 0 8px rgba(0,255,136,0.4)",
              }}
            />
            <span className="text-xs font-medium text-white/50 tracking-tight">YieldSage</span>
            <span className="text-xs text-white/20 ml-2 font-mono">© 2026</span>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6">
            {["Twitter", "Discord", "Telegram", "Docs", "Privacy"].map((link) => (
              <a
                key={link}
                href="#"
                className="text-[11px] text-white/25 hover:text-white/60 transition-colors font-mono"
              >
                {link}
              </a>
            ))}
          </div>

          {/* Mantle badge */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full"
            style={{
              border: "1px solid rgba(255,255,255,0.07)",
              background: "rgba(255,255,255,0.02)",
            }}
          >
            <div
              className="w-2 h-2 rounded-full"
              style={{ background: "rgba(0,255,136,0.8)" }}
            />
            <span className="text-[10px] font-mono text-white/30">Built on Mantle</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
