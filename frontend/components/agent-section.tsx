"use client"

import { useRef, useState, useEffect } from "react"
import { motion, useInView, AnimatePresence } from "framer-motion"

// ─── Real conversation drawn from actual bot.py / ai_service.py ──────────────
type MsgRole = "system_event" | "user" | "bot" | "bot_typing"

interface InlineBtn {
  label: string
  sub?: string
}
interface InlineRow {
  buttons: InlineBtn[]
}

interface ChatStep {
  id: string
  role: MsgRole
  text?: string
  rows?: InlineRow[]   // inline keyboard
  commandLabel?: string // for system event pills
  typeSpeed?: number   // ms per char, default 18
  pauseBefore?: number // ms to wait before showing (after prev finishes)
  isThinking?: boolean // show "…" before text appears
}

const CONVERSATION: ChatStep[] = [
  {
    id: "evt-start",
    role: "system_event",
    commandLabel: "You sent /start",
    pauseBefore: 600,
  },
  {
    id: "bot-welcome",
    role: "bot",
    pauseBefore: 800,
    isThinking: true,
    typeSpeed: 10,
    text: `👋 *Welcome to YieldSage, Alex!*\n\nI am your intelligent DeFi yield advisor for the *Mantle Network*.\n\nHere is what I can do for you:\n📈 *Paper Trading:* Simulate investing in yield pools and track APY changes.\n🚨 *Hourly Scoring:* Alert you if yields drop or better options appear.\n💬 *DeFi Assistant:* Ask me anything about yield opportunities!\n\nUse the buttons below to explore:`,
    rows: [
      { buttons: [{ label: "📊 View Yield Pools" }, { label: "💼 My Positions" }] },
      { buttons: [{ label: "📈 Simulate Trade" }, { label: "⚙️ Risk Preference" }] },
      { buttons: [{ label: "🔔 Alert Settings" }, { label: "💡 Prompts" }] },
      { buttons: [{ label: "❓ Help & Guide" }] },
    ],
  },
  {
    id: "user-q1",
    role: "user",
    pauseBefore: 1800,
    text: "What are the best stablecoin yields on Mantle right now?",
  },
  {
    id: "bot-thinking1",
    role: "bot",
    pauseBefore: 900,
    isThinking: true,
    typeSpeed: 11,
    text: `*Top Stable Pools Right Now*\n\n• *Clearpool USDT* — *17.50% APY* | TVL: $2.1M | 🟢 STABLE\n  Institutional private-credit pool. Best stable-tier yield on Mantle.\n\n• *Aave V3 USDC* — *7.02% APY* | TVL: $3.68M | 🟢 STABLE\n  Most battle-tested protocol globally. Lowest counterparty risk.\n\n• *Lendle USDT* — *11.80% APY* | TVL: $890K | 🟢 STABLE\n  Lending market with solid utilisation rate.\n\n*My Recommendation*\n\nFor a $1,000 conservative entry: split 70/30 between Clearpool and Aave V3. Clearpool carries higher yield, Aave anchors your downside.\n\nUse /trade to simulate this allocation.`,
  },
  {
    id: "user-q2",
    role: "user",
    pauseBefore: 2200,
    text: "Simulate a $2,000 trade on Clearpool USDT",
  },
  {
    id: "bot-trade",
    role: "bot",
    pauseBefore: 1000,
    isThinking: true,
    typeSpeed: 12,
    text: `✅ *Paper Trade Simulated Successfully!*\n\n💰 Invested: *$2,000.00*\n🏦 Pool: *Clearpool (USDT)*\n📈 Entry APY: *17.50%*\n\nI will now monitor this position hourly. You will receive alerts if the APY drops or if a better opportunity appears in the same risk tier!`,
    rows: [
      { buttons: [{ label: "💼 View My Positions" }] },
    ],
  },
  {
    id: "user-q3",
    role: "user",
    pauseBefore: 2000,
    text: "What's my projected return in 30 days?",
  },
  {
    id: "bot-projection",
    role: "bot",
    pauseBefore: 1100,
    isThinking: true,
    typeSpeed: 11,
    text: `*30-Day Projection — Clearpool USDT*\n\n• Principal: *$2,000.00*\n• APY: *17.50%*\n• Est. Return (30 days): *+$28.77*\n• Annualised: *+$350.00*\n\n*Risk Notes:*\n– Clearpool is institutional-grade but not overcollateralised.\n– Yield may fluctuate with credit market conditions.\n– I'll alert you if APY drops below *12%* — your safety threshold.\n\n💡 Tip: Use /alerts to configure your notification preferences.`,
  },
]

// ─── Helpers ─────────────────────────────────────────────────────────────────

function parseBoldText(text: string): React.ReactNode[] {
  const parts = text.split(/(\*[^*]+\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith("*") && part.endsWith("*")) {
      return <strong key={i} style={{ color: "rgba(255,255,255,0.92)", fontWeight: 600 }}>{part.slice(1, -1)}</strong>
    }
    // emoji bullet lines
    return <span key={i}>{part}</span>
  })
}

function renderText(text: string) {
  return text.split("\n").map((line, i) => (
    <span key={i} style={{ display: "block", lineHeight: 1.55 }}>
      {parseBoldText(line)}
    </span>
  ))
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1" style={{ padding: "10px 14px" }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "rgba(0,255,136,0.55)",
            display: "inline-block",
            animation: `tgBounce 1.1s ease-in-out ${i * 0.18}s infinite`,
          }}
        />
      ))}
    </div>
  )
}

interface RenderedStep {
  step: ChatStep
  displayText: string
  done: boolean
}

// ─── Main component ───────────────────────────────────────────────────────────

export function AgentSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const chatRef = useRef<HTMLDivElement>(null)
  const hasStartedRef = useRef(false)
  const inView = useInView(sectionRef, { once: true, margin: "0px" })

  const [rendered, setRendered] = useState<RenderedStep[]>([])
  const [typingIdx, setTypingIdx] = useState<number | null>(null)

  // auto-scroll
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" })
    }
  }, [rendered, typingIdx])

  // Orchestrator — uses a ref for the started flag so React Strict Mode
  // double-invocation doesn't prevent the animation from launching.
  useEffect(() => {
    if (!inView || hasStartedRef.current) return
    hasStartedRef.current = true

    let cancelled = false

    const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

    const run = async () => {
      while (!cancelled) {
        setRendered([])
        setTypingIdx(null)

        for (let idx = 0; idx < CONVERSATION.length; idx++) {
          if (cancelled) return
          const step = CONVERSATION[idx]

          await sleep(step.pauseBefore ?? 400)
          if (cancelled) return

          // Push skeleton
          setRendered((prev) => [
            ...prev,
            { step, displayText: "", done: false },
          ])

          if (step.role === "system_event") {
            setRendered((prev) => {
              const copy = [...prev]
              copy[copy.length - 1] = { ...copy[copy.length - 1], done: true }
              return copy
            })
            continue
          }

          // Show typing indicator for bot messages
          if (step.role === "bot") {
            setTypingIdx(idx)
            const thinkTime = step.isThinking ? 900 + Math.random() * 600 : 200
            await sleep(thinkTime)
            if (cancelled) return
            setTypingIdx(null)
          }

          // Typewriter
          const text = step.text ?? ""
          const speed = step.typeSpeed ?? 18
          let current = ""

          for (let ci = 0; ci < text.length; ci++) {
            if (cancelled) return
            current += text[ci]
            const snapshot = current
            setRendered((prev) => {
              const copy = [...prev]
              const last = { ...copy[copy.length - 1], displayText: snapshot }
              copy[copy.length - 1] = last
              return copy
            })
            const ch = text[ci]
            let delay = speed
            if (ch === "\n") delay = speed * 3
            else if ([".", "!", "?", ":"].includes(ch)) delay = speed * 5
            else if ([",", ";"].includes(ch)) delay = speed * 2
            await sleep(delay)
          }

          // Mark done (shows inline buttons)
          setRendered((prev) => {
            const copy = [...prev]
            copy[copy.length - 1] = { ...copy[copy.length - 1], done: true }
            return copy
          })
        }

        // Wait 8 seconds before looping again
        await sleep(8000)
      }
    }

    run()
    return () => { cancelled = true }
  }, [inView])

  return (
    <>
      <style>{`
        @keyframes tgBounce {
          0%,60%,100% { transform: translateY(0); opacity:.35 }
          30% { transform: translateY(-6px); opacity:1 }
        }
        @keyframes msgSlideIn {
          from { opacity:0; transform: translateY(10px) scale(0.97) }
          to   { opacity:1; transform: translateY(0)  scale(1) }
        }
        @keyframes pillFade {
          from { opacity:0; transform: scale(0.9) }
          to   { opacity:1; transform: scale(1) }
        }
        @keyframes cursorBlink {
          0%,100% { opacity:1 }
          50%      { opacity:0 }
        }
        @keyframes scanline {
          0%   { transform: translateY(-100%) }
          100% { transform: translateY(400%) }
        }
        @keyframes glowPulse {
          0%,100% { opacity:.4 }
          50%      { opacity:.7 }
        }
      `}</style>

      <section
        id="agent"
        className="relative px-6 md:px-12 py-28 md:py-40 overflow-hidden"
        style={{ background: "transparent" }}
      >
        {/* Section top rule */}
        <div
          className="absolute top-0 inset-x-0 h-px"
          style={{
            background:
              "linear-gradient(to right,transparent 0%,rgba(255,255,255,0.04) 25%,rgba(0,255,136,0.12) 50%,rgba(255,255,255,0.04) 75%,transparent 100%)",
          }}
        />

        {/* Deep ambient glow behind phone */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse 60% 50% at 30% 55%, rgba(0,255,136,0.04) 0%, transparent 70%)",
            animation: "glowPulse 4s ease-in-out infinite",
          }}
        />

        <div ref={sectionRef} className="max-w-6xl mx-auto relative z-10">
          {/* ── Header ── */}
          <div className="flex flex-col items-center text-center mb-16 md:mb-20">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full mb-8"
              style={{
                border: "1px solid rgba(0,255,136,0.18)",
                background: "rgba(0,255,136,0.05)",
              }}
            >
              <span
                style={{
                  width: 6, height: 6, borderRadius: "50%",
                  background: "rgba(0,255,136,1)",
                  boxShadow: "0 0 8px rgba(0,255,136,0.9)",
                  display: "inline-block",
                  animation: "glowPulse 1.5s ease-in-out infinite",
                }}
              />
              <span className="text-[10px] tracking-[0.32em] text-white/45 uppercase font-mono">
                AI Agent · Live on Telegram
              </span>
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 24 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.9, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
              className="text-3xl md:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.08] mb-5"
              style={{ color: "rgba(255,255,255,0.92)" }}
            >
              Your yield advisor,
              <br />
              <span style={{ color: "rgba(255,255,255,0.28)" }}>
                always in your pocket.
              </span>
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.8, delay: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="text-sm md:text-[15px] leading-relaxed max-w-[480px]"
              style={{ color: "rgba(255,255,255,0.32)" }}
            >
              Ask in plain English. Get live risk-scored opportunities, protocol
              health signals, and paper-trade simulations — right inside Telegram.
            </motion.p>
          </div>

          {/* ── Grid: phone + right panel ── */}
          <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-10 xl:gap-16 items-start">

            {/* ─── Phone mockup ─── */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 1, delay: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="relative mx-auto lg:mx-0"
              style={{ width: "100%", maxWidth: 380 }}
            >
              {/* Outer glow */}
              <div
                className="absolute -inset-6 rounded-[44px] pointer-events-none"
                style={{
                  background:
                    "radial-gradient(ellipse at 50% 50%, rgba(0,255,136,0.07) 0%, transparent 70%)",
                  filter: "blur(20px)",
                  animation: "glowPulse 3s ease-in-out infinite",
                }}
              />

              {/* Outer Phone Shell (iOS Bezel Frame) */}
              <div
                className="relative rounded-[48px] p-[10px] bg-[#0c0d0f] border border-white/10 shadow-[0_0_0_4px_#1e1f22,0_0_0_5px_#2b2d30,0_40px_80px_rgba(0,0,0,0.85)] select-none"
                style={{
                  width: "100%",
                  maxWidth: 380,
                  margin: "0 auto",
                }}
              >
                {/* Physical Side Buttons */}
                {/* Silent Switch */}
                <div className="absolute left-[-5px] top-[90px] w-[5px] h-[30px] bg-[#1e1f22] rounded-l-md border-y border-l border-white/5" />
                {/* Volume Up */}
                <div className="absolute left-[-5px] top-[140px] w-[5px] h-[50px] bg-[#1e1f22] rounded-l-md border-y border-l border-white/5" />
                {/* Volume Down */}
                <div className="absolute left-[-5px] top-[205px] w-[5px] h-[50px] bg-[#1e1f22] rounded-l-md border-y border-l border-white/5" />
                {/* Power Button */}
                <div className="absolute right-[-5px] top-[160px] w-[5px] h-[75px] bg-[#1e1f22] rounded-r-md border-y border-r border-white/5" />

                {/* Inner Screen */}
                <div
                  className="relative rounded-[38px] overflow-hidden bg-[#17212b] border border-black/40 shadow-inner"
                >
                  {/* Dynamic Island */}
                  <div className="absolute top-3 left-1/2 -translate-x-1/2 w-28 h-6 bg-black rounded-full z-50 flex items-center justify-between px-3 border border-white/5 shadow-md">
                    {/* Camera */}
                    <div className="w-2 h-2 rounded-full bg-[#0d0d0d] border border-white/5 flex items-center justify-center">
                      <div className="w-1 h-1 rounded-full bg-[#180838]" />
                    </div>
                    {/* Speaker */}
                    <div className="w-10 h-0.5 bg-[#0a0a0a] rounded-full" />
                  </div>

                  {/* Status bar */}
                  <div
                    className="flex items-center justify-between px-6 pt-4 pb-2 relative z-40"
                    style={{ background: "#17212b" }}
                  >
                    <span className="text-[10px] font-semibold text-white/80 font-mono leading-none">9:41</span>
                    <div className="w-28 h-4" />
                    <div className="flex items-center gap-1.5 leading-none">
                      {/* signal */}
                      <div className="flex items-end gap-[1px]">
                        {[3, 5, 7, 9].map((h) => (
                          <div key={h} className="bg-white/70" style={{ width: 1.5, height: h, borderRadius: 0.5 }} />
                        ))}
                      </div>
                      {/* wifi */}
                      <svg width="11" height="9" viewBox="0 0 13 10" fill="none" className="text-white/70">
                        <path d="M6.5 8.5L8 7C7.4 6.4 6.6 6 6.5 6C6.4 6 5.6 6.4 5 7L6.5 8.5Z" fill="currentColor"/>
                        <path d="M6.5 10L6.5 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                      </svg>
                      {/* battery */}
                      <div className="border border-white/40 rounded-[3px] p-[1px] flex items-center" style={{ width: 18, height: 9.5 }}>
                        <div className="h-full bg-white/80 rounded-[0.5px]" style={{ width: "70%" }} />
                      </div>
                    </div>
                  </div>

                {/* Telegram chat header */}
                <div
                  className="flex items-center gap-3 px-4 py-3"
                  style={{
                    background: "#17212b",
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                  }}
                >
                  {/* Avatar */}
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-base flex-shrink-0"
                    style={{
                      background: "linear-gradient(135deg, rgba(0,255,136,0.3) 0%, rgba(0,200,100,0.15) 100%)",
                      border: "1.5px solid rgba(0,255,136,0.25)",
                    }}
                  >
                    🤖
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-semibold text-white/85 leading-tight">YieldSage</div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#4ade80", display: "inline-block" }} />
                      <span className="text-[10px] text-white/35 font-mono">online</span>
                    </div>
                  </div>
                  {/* Header actions */}
                  <div className="flex items-center gap-3 opacity-40">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
                  </div>
                </div>

                {/* Messages area */}
                <div
                  ref={chatRef}
                  className="flex flex-col gap-1 overflow-y-auto px-3 py-3"
                  style={{
                    background: "#0e1621",
                    minHeight: 420,
                    maxHeight: 480,
                    scrollbarWidth: "none",
                    position: "relative",
                  }}
                >
                  {/* Scanline effect */}
                  <div
                    className="absolute inset-0 pointer-events-none"
                    style={{ overflow: "hidden", zIndex: 10 }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        background:
                          "repeating-linear-gradient(0deg, transparent 0px, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)",
                        pointerEvents: "none",
                      }}
                    />
                  </div>

                  {/* Date chip */}
                  <div className="flex justify-center my-1">
                    <span
                      className="text-[10px] font-mono px-2.5 py-1 rounded-full"
                      style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.3)" }}
                    >
                      Today
                    </span>
                  </div>

                  <AnimatePresence initial={false}>
                    {rendered.map((r) => {
                      const { step, displayText, done } = r

                      // ── System event pill ──
                      if (step.role === "system_event") {
                        return (
                          <motion.div
                            key={step.id}
                            initial={{ opacity: 0, scale: 0.85 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.3 }}
                            className="flex justify-center my-1"
                          >
                            <span
                              className="text-[10px] font-mono px-3 py-1 rounded-full"
                              style={{
                                background: "rgba(0,255,136,0.08)",
                                border: "1px solid rgba(0,255,136,0.15)",
                                color: "rgba(0,255,136,0.7)",
                              }}
                            >
                              {step.commandLabel}
                            </span>
                          </motion.div>
                        )
                      }

                      // ── User bubble ──
                      if (step.role === "user") {
                        return (
                          <motion.div
                            key={step.id}
                            initial={{ opacity: 0, x: 20, scale: 0.95 }}
                            animate={{ opacity: 1, x: 0, scale: 1 }}
                            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                            className="flex justify-end mb-1"
                          >
                            <div
                              className="max-w-[78%] text-[12px] leading-relaxed px-3.5 py-2"
                              style={{
                                background: "#2b5278",
                                borderRadius: "14px 14px 4px 14px",
                                color: "rgba(255,255,255,0.88)",
                              }}
                            >
                              {displayText}
                              {!done && (
                                <span style={{ animation: "cursorBlink 0.8s ease infinite", marginLeft: 1 }}>▌</span>
                              )}
                              <span
                                className="block text-right text-[9px] mt-0.5 font-mono"
                                style={{ color: "rgba(255,255,255,0.3)" }}
                              >
                                {done ? "✓✓ 9:41" : ""}
                              </span>
                            </div>
                          </motion.div>
                        )
                      }

                      // ── Bot bubble ──
                      if (step.role === "bot") {
                        return (
                          <motion.div
                            key={step.id}
                            initial={{ opacity: 0, x: -16, scale: 0.96 }}
                            animate={{ opacity: 1, x: 0, scale: 1 }}
                            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                            className="flex flex-col items-start mb-1.5"
                          >
                            <div
                              className="max-w-[86%] text-[11.5px] px-3.5 py-2.5"
                              style={{
                                background: "#182533",
                                borderRadius: "4px 14px 14px 14px",
                                color: "rgba(255,255,255,0.75)",
                                border: "1px solid rgba(0,255,136,0.07)",
                                lineHeight: 1.55,
                              }}
                            >
                              {displayText ? renderText(displayText) : null}
                              {!done && displayText && (
                                <span style={{ animation: "cursorBlink 0.8s ease infinite" }}>▌</span>
                              )}
                              {done && (
                                <span
                                  className="block text-[9px] mt-1 font-mono"
                                  style={{ color: "rgba(255,255,255,0.25)" }}
                                >
                                  9:41
                                </span>
                              )}
                            </div>

                            {/* Inline keyboard */}
                            {done && step.rows && (
                              <motion.div
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.3, delay: 0.1 }}
                                className="max-w-[86%] mt-1.5 flex flex-col gap-1 w-full"
                              >
                                {step.rows.map((row, ri) => (
                                  <div key={ri} className="flex gap-1">
                                    {row.buttons.map((btn, bi) => (
                                      <div
                                        key={bi}
                                        className="flex-1 text-center text-[10.5px] font-medium py-1.5 px-2 rounded-lg cursor-pointer transition-all select-none"
                                        style={{
                                          background: "rgba(0,122,204,0.25)",
                                          border: "1px solid rgba(0,122,204,0.3)",
                                          color: "rgba(100,200,255,0.9)",
                                          whiteSpace: "nowrap",
                                          overflow: "hidden",
                                          textOverflow: "ellipsis",
                                        }}
                                        onMouseEnter={(e) => {
                                          (e.currentTarget as HTMLDivElement).style.background = "rgba(0,122,204,0.4)"
                                        }}
                                        onMouseLeave={(e) => {
                                          (e.currentTarget as HTMLDivElement).style.background = "rgba(0,122,204,0.25)"
                                        }}
                                      >
                                        {btn.label}
                                      </div>
                                    ))}
                                  </div>
                                ))}
                              </motion.div>
                            )}
                          </motion.div>
                        )
                      }

                      return null
                    })}
                  </AnimatePresence>

                  {/* Typing indicator — renders between messages */}
                  <AnimatePresence>
                    {typingIdx !== null && (
                      <motion.div
                        key="typing"
                        initial={{ opacity: 0, x: -12, scale: 0.92 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.88 }}
                        transition={{ duration: 0.2 }}
                        className="flex items-start gap-2"
                      >
                        <div
                          style={{
                            background: "#182533",
                            borderRadius: "4px 14px 14px 14px",
                            border: "1px solid rgba(0,255,136,0.07)",
                          }}
                        >
                          <TypingIndicator />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Input bar */}
                <div
                  className="flex items-center gap-2 px-3 py-3"
                  style={{
                    background: "#17212b",
                    borderTop: "1px solid rgba(255,255,255,0.05)",
                  }}
                >
                  <div
                    className="flex-1 flex items-center gap-2 px-3 py-2 rounded-full"
                    style={{
                      background: "#242f3d",
                      border: "1px solid rgba(255,255,255,0.06)",
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="rgba(255,255,255,0.2)">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    <span className="text-[11px] flex-1" style={{ color: "rgba(255,255,255,0.18)" }}>
                      Message…
                    </span>
                  </div>
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center"
                    style={{ background: "rgba(0,122,204,0.4)" }}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="rgba(100,200,255,0.9)">
                      <path d="M2 21L23 12 2 3v7l15 2-15 2z"/>
                    </svg>
                  </div>
                </div>

                  {/* iOS Home Indicator */}
                  <div
                    className="flex justify-center pt-1.5 pb-2.5"
                    style={{ background: "#17212b" }}
                  >
                    <div className="w-32 h-1 bg-white/30 rounded-full" />
                  </div>
                </div>
              </div>
            </motion.div>

            {/* ─── Right panel ─── */}
            <motion.div
              initial={{ opacity: 0, x: 24 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.9, delay: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-col gap-6 pt-2 lg:pt-8"
            >
              {/* Feature list */}
              {[
                {
                  icon: "📊",
                  title: "Live Yield Intelligence",
                  desc: "Real-time APY data from every major Mantle protocol — scored, ranked, and risk-tiered automatically.",
                },
                {
                  icon: "📈",
                  title: "Paper Trade Simulation",
                  desc: "Simulate any investment and track it hourly. Get instant alerts when your position underperforms.",
                },
                {
                  icon: "🚨",
                  title: "Autonomous Monitoring",
                  desc: "YieldSage runs in the background every hour. It finds better opportunities and pushes them to you before you miss them.",
                },
                {
                  icon: "💬",
                  title: "Conversational DeFi Advisor",
                  desc: "Ask anything — portfolio advice, protocol breakdowns, risk analysis. Powered by a multi-LLM cascade with zero hallucination laws.",
                },
              ].map((f, i) => (
                <motion.div
                  key={f.title}
                  initial={{ opacity: 0, y: 16 }}
                  animate={inView ? { opacity: 1, y: 0 } : {}}
                  transition={{ duration: 0.65, delay: 0.5 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}
                  className="flex gap-4 items-start"
                >
                  <div
                    className="w-9 h-9 rounded-xl flex items-center justify-center text-base flex-shrink-0 mt-0.5"
                    style={{
                      background: "rgba(0,255,136,0.07)",
                      border: "1px solid rgba(0,255,136,0.12)",
                    }}
                  >
                    {f.icon}
                  </div>
                  <div>
                    <div className="text-sm font-semibold mb-1" style={{ color: "rgba(255,255,255,0.78)" }}>
                      {f.title}
                    </div>
                    <div className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.32)" }}>
                      {f.desc}
                    </div>
                  </div>
                </motion.div>
              ))}

              {/* CTA */}
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.8, delay: 0.95, ease: [0.22, 1, 0.36, 1] }}
                className="mt-6 flex flex-col items-center justify-center text-center w-full"
              >
                <a
                  href="https://t.me/YieldSageBot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-3 px-7 py-4 rounded-full text-sm font-semibold tracking-wide transition-all"
                  style={{
                    background: "rgba(0,255,136,1)",
                    color: "#050505",
                    boxShadow: "0 0 24px rgba(0,255,136,0.25)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = "0 0 48px rgba(0,255,136,0.45)"
                    e.currentTarget.style.transform = "translateY(-2px)"
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = "0 0 24px rgba(0,255,136,0.25)"
                    e.currentTarget.style.transform = "translateY(0)"
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.96 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                  </svg>
                  Launch YieldSage AI Agent
                </a>

                <div className="flex items-center justify-center gap-4 mt-5">
                  <a
                    href="https://x.com/yieldsageai"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-xs transition-all"
                    style={{ color: "rgba(255,255,255,0.3)" }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.65)" }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(255,255,255,0.3)" }}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.733-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                    </svg>
                    @yieldsageai
                  </a>
                  <span style={{ color: "rgba(255,255,255,0.1)" }}>·</span>
                  <a
                    href="https://t.me/YieldSageBot"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-xs transition-all"
                    style={{ color: "rgba(0,255,136,0.45)" }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = "rgba(0,255,136,0.85)" }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = "rgba(0,255,136,0.45)" }}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.96 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                    </svg>
                    @YieldSageBot
                  </a>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>
    </>
  )
}
