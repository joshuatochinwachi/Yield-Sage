"use client"

import { useRef } from "react"
import { motion, useInView } from "framer-motion"
import { Brain, ShieldCheck, Activity, TrendingUp, Bell, Layers } from "lucide-react"

const features = [
  {
    icon: Brain,
    label: "AI Yield Ranking",
    description:
      "A live leaderboard scoring every tracked Mantle pool by risk-adjusted APY, TVL depth, and protocol health — refreshed every hour via Dune Analytics.",
    stat: "Hourly",
    statLabel: "Scoring cadence",
    color: "rgba(0,255,136,",
  },
  {
    icon: ShieldCheck,
    label: "Risk-Adjusted Allocation",
    description:
      "Select your risk appetite. Pools are automatically classified into Stable, Moderate, or Aggressive tiers using a multi-factor scoring engine.",
    stat: "3 Tiers",
    statLabel: "Risk profiles",
    color: "rgba(99,179,237,",
  },
  {
    icon: Activity,
    label: "On-Chain Verification",
    description:
      "No black boxes. Every pool recommendation links directly to its on-chain address on MantleScan so you can verify the contract before you invest.",
    stat: "100%",
    statLabel: "On-chain verifiable",
    color: "rgba(0,255,136,",
  },
  {
    icon: TrendingUp,
    label: "Paper Trading Simulation",
    description:
      "Test any yield strategy with simulated capital before committing real funds. Track performance hourly and get alerted when your paper position underperforms.",
    stat: "1 Click",
    statLabel: "Simulation entry",
    color: "rgba(246,173,85,",
  },
  {
    icon: Bell,
    label: "Real-Time Telegram Alerts",
    description:
      "Instant push notifications the moment a superior risk-adjusted pool opens up on Mantle. Never miss a yield shift while you are away from the screen.",
    stat: "<1 min",
    statLabel: "Alert latency",
    color: "rgba(159,122,234,",
  },
  {
    icon: Layers,
    label: "Multi-Protocol Coverage",
    description:
      "Tracks every major DeFi protocol deployed on Mantle — including Merchant Moe, Aave, Agni Finance, Fluxion Network, Ondo, Clearpool, and more — all in a single unified dashboard.",
    stat: "All",
    statLabel: "Mantle protocols",
    color: "rgba(251,113,133,",
  },
]

function FeatureCard({
  feature,
  index,
}: {
  feature: (typeof features)[0]
  index: number
}) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-60px" })
  const Icon = feature.icon

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 32 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{
        duration: 0.7,
        delay: index * 0.1,
        ease: [0.22, 1, 0.36, 1],
      }}
      className="group relative flex flex-col gap-5 p-6 rounded-2xl overflow-hidden transition-all duration-500"
      style={{
        background:
          "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)",
        border: "1px solid rgba(255,255,255,0.07)",
        backdropFilter: "blur(24px)",
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLDivElement
        el.style.borderColor = `${feature.color}0.2)`
        el.style.background =
          `linear-gradient(135deg, ${feature.color}0.06) 0%, rgba(255,255,255,0.01) 100%)`
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLDivElement
        el.style.borderColor = "rgba(255,255,255,0.07)"
        el.style.background =
          "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)"
      }}
    >
      {/* Corner glow on hover */}
      <div
        className="absolute -top-12 -right-12 w-32 h-32 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"
        style={{
          background: `radial-gradient(circle, ${feature.color}0.12) 0%, transparent 70%)`,
        }}
      />

      {/* Icon */}
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center"
        style={{
          background: `${feature.color}0.1)`,
          border: `1px solid ${feature.color}0.2)`,
        }}
      >
        <Icon className="w-4.5 h-4.5" style={{ color: `${feature.color}0.9)` }} size={18} />
      </div>

      {/* Label + description */}
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold text-white/85 tracking-tight">{feature.label}</h3>
        <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.38)" }}>
          {feature.description}
        </p>
      </div>

      {/* Stat */}
      <div className="mt-auto pt-4 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
        <div className="flex items-baseline gap-2">
          <span
            className="text-xl font-semibold tracking-tight"
            style={{ color: `${feature.color}0.9)` }}
          >
            {feature.stat}
          </span>
          <span className="text-[10px] text-white/30 font-mono">{feature.statLabel}</span>
        </div>
      </div>
    </motion.div>
  )
}

export function FeaturesSection() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-80px" })

  return (
    <section
      id="features"
      className="relative py-28 md:py-40 px-6 md:px-12"
      style={{ background: "transparent" }}
    >
      {/* Ambient glow background */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 70% 50% at 50% 50%, rgba(0,255,136,0.03) 0%, transparent 65%)",
        }}
      />

      <div className="max-w-6xl mx-auto relative z-10">
        {/* Section header */}
        <div ref={ref} className="text-center mb-16 md:mb-20">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="text-[10px] tracking-[0.4em] uppercase font-mono mb-5"
            style={{ color: "rgba(0,255,136,0.6)" }}
          >
            Core Capabilities
          </motion.p>

          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="text-3xl md:text-5xl font-semibold tracking-tight leading-tight"
            style={{ color: "rgba(255,255,255,0.9)" }}
          >
            Everything the market
            <br />
            <span style={{ color: "rgba(255,255,255,0.3)" }}>demands. Nothing it doesn't.</span>
          </motion.h2>
        </div>

        {/* Feature grid — 3×2 for even orientation */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature, i) => (
            <FeatureCard key={feature.label} feature={feature} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
