"use client"

import { useRef, useEffect, useState } from "react"
import { useScroll, useTransform, useSpring, motion, type MotionValue } from "framer-motion"
import { ScrollCanvas } from "@/components/scroll-canvas"

interface ScrollytellingSectionProps {
  section1Frames: HTMLImageElement[]
  section2Frames: HTMLImageElement[]
  preloadSection2: () => void
}

// Flanking Label component: draws 1px horizontal lines from left to right on view
function FlankingLabel({ text, slow = false }: { text: string; slow?: boolean }) {
  const duration = slow ? 1.5 : 0.8
  return (
    <div className="flex items-center justify-center gap-3.5 text-[11px] tracking-[0.3em] font-sans text-white/40 uppercase font-bold select-none">
      <motion.span
        className="h-[1px] bg-white/20 block origin-left"
        initial={{ scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration, ease: [0.22, 1, 0.36, 1] }}
        style={{ width: "32px" }}
      />
      <span>{text}</span>
      <motion.span
        className="h-[1px] bg-white/20 block origin-left"
        initial={{ scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration, ease: [0.22, 1, 0.36, 1] }}
        style={{ width: "32px" }}
      />
    </div>
  )
}

// Cinematic overlay component that fades/translates based on custom scroll ranges
function CinematicOverlay({
  active,
  scrollYProgress,
  range,
  position,
  fadeInRange = 0.15,
  fadeOutRange = 0.15,
  children,
}: {
  active: boolean
  scrollYProgress: MotionValue<number>
  range: [number, number]
  position: "bottom-left" | "bottom-right" | "center-bottom" | "center" | "center-top" | "top-center-high"
  fadeInRange?: number
  fadeOutRange?: number
  children: React.ReactNode
}) {
  const start = range[0]
  const end = range[1]
  const duration = end - start

  const fadeInEnd = start + duration * fadeInRange
  const fadeOutStart = end - duration * fadeOutRange

  // Cinematic scroll binding (Enter: opacity 0->1, y 20px->0 | Exit: opacity 1->0, y 0->-10px)
  const opacity = useTransform(
    scrollYProgress,
    [start, fadeInEnd, fadeOutStart, end],
    [0, 1, 1, 0]
  )

  const y = useTransform(
    scrollYProgress,
    [start, fadeInEnd, fadeOutStart, end],
    [20, 0, 0, -10]
  )

  let positionClass = ""
  switch (position) {
    case "bottom-left":
      positionClass = "bottom-24 left-6 md:left-24 text-left items-start"
      break
    case "bottom-right":
      positionClass = "bottom-24 right-6 md:right-24 text-right items-end"
      break
    case "center-bottom":
      positionClass = "bottom-24 left-1/2 -translate-x-1/2 text-center items-center"
      break
    case "center":
      positionClass = "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center items-center w-full max-w-4xl px-8"
      break
    case "center-top":
      positionClass = "top-[25%] left-1/2 -translate-x-1/2 text-center items-center w-full max-w-4xl px-8"
      break
    case "top-center-high":
      // Sits at top-1/5 of the screen — clearly in the upper band, never buried
      positionClass = "top-[18%] left-1/2 -translate-x-1/2 text-center items-center w-full max-w-4xl px-8"
      break
  }

  return (
    <motion.div
      style={{ opacity, y }}
      className={`absolute z-30 pointer-events-none flex flex-col gap-4 max-w-xl md:max-w-2xl select-none ${positionClass}`}
    >
      {active && children}
    </motion.div>
  )
}

// Deterministic seeded PRNG — identical output on server and client to avoid hydration mismatches.
// Uses a simple mulberry32 algorithm.
function seededRandom(seed: number) {
  let t = (seed + 0x6d2b79f5) | 0
  t = Math.imul(t ^ (t >>> 15), t | 1)
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296
}

// Pre-compute particle data at module level so both SSR and client get the exact same values.
const PARTICLE_DATA = [...Array(20)].map((_, i) => ({
  width: (seededRandom(i * 6 + 1) * 1.5 + 0.8).toFixed(3),
  height: (seededRandom(i * 6 + 2) * 1.5 + 0.8).toFixed(3),
  left: (seededRandom(i * 6 + 3) * 100).toFixed(3),
  top: (seededRandom(i * 6 + 4) * 100).toFixed(3),
  duration: (seededRandom(i * 6 + 5) * 12 + 10).toFixed(3),
  delay: (seededRandom(i * 6 + 6) * 10).toFixed(3),
}))

// Particle effect wrapper for floating ambient elements during peaks
function AmbientParticles({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  // Move particles slowly upwards as you scroll down
  const yOffset = useTransform(scrollYProgress, [0, 1], [0, -180])

  // Particles fade in only during Phase 5 & 6 of both sections (Sec 1: 400-600vh, Sec 2: 1100-1300vh)
  const opacity = useTransform(
    scrollYProgress,
    [
      0,
      400 / 1300,
      430 / 1300,
      570 / 1300,
      600 / 1300,
      1100 / 1300,
      1130 / 1300,
      1280 / 1300,
      1.0,
    ],
    [0, 0, 0.25, 0.25, 0, 0, 0.25, 0.25, 0]
  )

  return (
    <motion.div style={{ y: yOffset, opacity }} className="absolute inset-0 pointer-events-none overflow-hidden z-20">
      {PARTICLE_DATA.map((p, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-white"
          style={{
            width: p.width + "px",
            height: p.height + "px",
            left: p.left + "%",
            top: p.top + "%",
            animation: `float-particle ${p.duration}s linear infinite`,
            animationDelay: `-${p.delay}s`,
          }}
        />
      ))}
    </motion.div>
  )
}

function ScrollIndicator({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  // Fade out quickly as user scrolls down (fades out completely by 50vh)
  const opacity = useTransform(scrollYProgress, [0, 50 / 1300], [1, 0])
  const y = useTransform(scrollYProgress, [0, 50 / 1300], [0, 20])
  
  return (
    <motion.div 
      style={{ opacity, y }}
      className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30 flex flex-col items-center gap-3 pointer-events-none select-none"
    >
      <div className="text-[9px] font-sans tracking-[0.4em] uppercase text-white/40 font-bold">
        Scroll to Explore
      </div>
      
      {/* Sleek Mouse Shape */}
      <div 
        className="w-[22px] h-[36px] rounded-full border border-white/20 flex justify-center pt-1.5 relative overflow-hidden"
        style={{
          background: "linear-gradient(to bottom, rgba(255,255,255,0.03) 0%, transparent 100%)",
          backdropFilter: "blur(4px)",
        }}
      >
        {/* Animated Glowing Wheel */}
        <motion.div 
          animate={{ 
            y: [0, 14],
            opacity: [1, 0] 
          }}
          transition={{ 
            duration: 1.5, 
            repeat: Infinity, 
            ease: "easeOut" 
          }}
          className="w-[3px] h-[6px] rounded-full"
          style={{
            background: "rgba(0,255,136,0.9)",
            boxShadow: "0 0 8px rgba(0,255,136,0.6), 0 0 16px rgba(0,255,136,0.3)",
          }}
        />
      </div>
      
      {/* Bouncing Chevron */}
      <motion.div
        animate={{ y: [0, 6, 0] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        className="mt-1"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(0,255,136,0.6)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 9l6 6 6-6"/>
        </svg>
      </motion.div>
    </motion.div>
  )
}

export function ScrollytellingSection({
  section1Frames,
  section2Frames,
  preloadSection2,
}: ScrollytellingSectionProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [activePhase, setActivePhase] = useState(1)

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  })

  // Spring-smoothed scroll progress for organic fluid inertia across all overlays
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 50,
    damping: 20,
    restDelta: 0.0005,
  })

  // Trigger background preloading of Section 2 when user hits Section 1 Phase 3 (200vh / 1300vh = 0.15)
  useEffect(() => {
    const unsubscribe = smoothProgress.on("change", (latest) => {
      const scrollVh = latest * 1300

      // Call preloader once we reach 200vh
      if (scrollVh >= 200) {
        preloadSection2()
      }

      // Track active phase to coordinate stagger entries
      let phase = 1
      if (scrollVh < 100) phase = 1
      else if (scrollVh < 200) phase = 2
      else if (scrollVh < 300) phase = 3
      else if (scrollVh < 400) phase = 4
      else if (scrollVh < 500) phase = 5
      else if (scrollVh < 600) phase = 6
      else if (scrollVh < 700) phase = 7 // Transition
      else if (scrollVh < 800) phase = 8 // S2 P1
      else if (scrollVh < 900) phase = 9 // S2 P2
      else if (scrollVh < 1000) phase = 10 // S2 P3
      else if (scrollVh < 1100) phase = 11 // S2 P4
      else if (scrollVh < 1200) phase = 12 // S2 P5
      else phase = 13 // S2 P6

      setActivePhase(phase)
    })

    return () => unsubscribe()
  }, [smoothProgress, preloadSection2])

  // Canvas Opacity Sync — must align exactly with scroll-canvas.tsx cutoff points:
  // SECTION_1_CUTOFF = 590/1300, SECTION_2_START = 710/1300
  // Fade-out starts at 570vh (gives 20vh to smoothly fade before canvas stops drawing)
  // Fade-in ends at 730vh (gives 20vh to smoothly fade back in after canvas resumes)
  // The total blackout zone (590–710) is held at 0 in between.
  const canvasOpacity = useTransform(
    smoothProgress,
    [
      0,
      570 / 1300,  // start fading OUT
      590 / 1300,  // canvas stops drawing (SECTION_1_CUTOFF) — must be fully 0 by here
      710 / 1300,  // canvas resumes drawing (SECTION_2_START) — begin fading IN from 0
      730 / 1300,  // fully opaque again
      1.0,
    ],
    [1, 1, 0, 0, 1, 1]
  )

  // Framer Motion staggered child variants for text entrance delays
  const staggerContainer = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.25,
      },
    },
  }

  const staggerItem = {
    hidden: { opacity: 0, y: 15 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: 1.0, ease: [0.22, 1, 0.36, 1] },
    },
  }

  const diagnosticStagger = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
      },
    },
  }

  const diagnosticItem = {
    hidden: { opacity: 0, scale: 0.98 },
    show: {
      opacity: 1,
      scale: 1,
      transition: { duration: 0.8, ease: "easeOut" },
    },
  }

  return (
    <section
      ref={containerRef}
      className="relative"
      style={{ height: "1300vh" }} // Total scroll real-estate
    >
      {/* Floating premium fintech header (Navbar) */}
      <header className="fixed top-0 left-0 w-full z-40" style={{ isolation: "isolate" }}>
        {/* Cinematic glow beam emanating from center of nav — inspired by hollow-scan-ui */}
        <div
          className="absolute inset-x-0 top-0 h-[120px] pointer-events-none"
          style={{
            background: "radial-gradient(ellipse 60% 80px at 50% 0%, rgba(0,255,136,0.10) 0%, transparent 100%)",
          }}
        />
        {/* Thin glowing border at bottom of nav */}
        <div
          className="absolute inset-x-0 bottom-0 h-px pointer-events-none"
          style={{
            background: "linear-gradient(to right, transparent 0%, rgba(0,255,136,0.08) 20%, rgba(0,255,136,0.25) 50%, rgba(0,255,136,0.08) 80%, transparent 100%)",
          }}
        />

        <div
          className="flex items-center justify-between px-6 md:px-12 py-6"
          style={{
            background: "linear-gradient(to bottom, rgba(5,5,5,0.75) 0%, rgba(5,5,5,0.2) 100%)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
          }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-5 h-5 rounded-full"
              style={{
                background: "radial-gradient(circle, rgba(0,255,136,0.9) 0%, rgba(0,255,136,0.3) 100%)",
                boxShadow: "0 0 12px rgba(0,255,136,0.5), 0 0 24px rgba(0,255,136,0.2)",
              }}
            />
            <span className="text-sm font-semibold tracking-tight text-white/90 font-sans">YieldSage</span>
          </div>

          <nav className="hidden md:flex items-center gap-8">
            {["Protocol", "Intelligence", "Allocation", "Docs"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="text-xs text-white/40 hover:text-white/80 transition-colors tracking-wide font-sans font-medium relative group py-1 select-none"
              >
                {item}
                {/* Expanding glowing underline on hover */}
                <span className="absolute bottom-0 left-0 w-0 h-[1.5px] bg-[rgba(0,255,136,0.85)] shadow-[0_0_8px_rgba(0,255,136,0.6)] group-hover:w-full transition-all duration-300" />
              </a>
            ))}
          </nav>

          <a
            href="#features"
            className="text-[11px] font-sans font-semibold tracking-wider uppercase px-5 py-2.5 rounded-full border transition-all select-none"
            style={{
              borderColor: "rgba(0,255,136,0.25)",
              color: "rgba(0,255,136,0.9)",
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLAnchorElement
              el.style.background = "rgba(0,255,136,0.08)"
              el.style.borderColor = "rgba(0,255,136,0.6)"
              el.style.boxShadow = "0 0 20px rgba(0,255,136,0.2), 0 0 40px rgba(0,255,136,0.1)"
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLAnchorElement
              el.style.background = "transparent"
              el.style.borderColor = "rgba(0,255,136,0.25)"
              el.style.boxShadow = "none"
            }}
          >
            Request Access
          </a>
        </div>
      </header>

      {/* Sticky full-screen viewport */}
      <div className="sticky top-0 h-screen w-full overflow-hidden bg-[#050505]">
        
        {/* CRT Scanline grain filter */}
        <div className="absolute inset-0 pointer-events-none z-20 scanlines opacity-[0.03]" />

        {/* Cinematic Vignette overlay */}
        <div className="absolute inset-0 pointer-events-none z-20 vignette" />

        {/* Drifting ambient particles */}
        <AmbientParticles scrollYProgress={smoothProgress} />

        {/* Global Scroll Indicator (visible only at the very top) */}
        <ScrollIndicator scrollYProgress={smoothProgress} />

        {/* Fullscreen Canvas for sequence scrub */}
        <motion.div style={{ opacity: canvasOpacity }} className="absolute inset-0 z-10 w-full h-full">
          <ScrollCanvas
            scrollProgress={smoothProgress}
            section1Frames={section1Frames}
            section2Frames={section2Frames}
          />
        </motion.div>

        {/* -------------------- SECTION 1: PLANT SEQUENCE OVERLAYS -------------------- */}

        {/* Phase 1 — Frames 1–40 | Scroll 0–100vh */}
        <CinematicOverlay
          active={activePhase === 1}
          scrollYProgress={smoothProgress}
          range={[0, 100 / 1300]}
          position="bottom-left"
        >
          <FlankingLabel text="Mantle Network" />
          <h2 className="text-4xl sm:text-5xl md:text-6xl font-serif text-white/90 tracking-tight leading-[1.1] font-light mt-1">
            Something is growing.
          </h2>
        </CinematicOverlay>

        {/* Phase 2 — Frames 41–80 | Scroll 100–200vh */}
        <CinematicOverlay
          active={activePhase === 2}
          scrollYProgress={smoothProgress}
          range={[100 / 1300, 200 / 1300]}
          position="bottom-left"
        >
          <FlankingLabel text="The Opportunity" />
          <motion.div variants={staggerContainer} initial="hidden" animate="show" className="flex flex-col gap-2.5 mt-2">
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light">
              Billions in liquidity.
            </motion.h3>
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light">
              Dozens of protocols.
            </motion.h3>
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light">
              Endless yield.
            </motion.h3>
          </motion.div>
        </CinematicOverlay>

        {/* Phase 3 — Frames 81–120 | Scroll 200–300vh */}
        <CinematicOverlay
          active={activePhase === 3}
          scrollYProgress={smoothProgress}
          range={[200 / 1300, 300 / 1300]}
          position="bottom-right"
        >
          <FlankingLabel text="The Problem" />
          <motion.div variants={staggerContainer} initial="hidden" animate="show" className="flex flex-col gap-4 mt-2">
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light">
              Most of it goes untapped.
            </motion.h3>
            <motion.p variants={staggerItem} className="text-sm md:text-base font-sans text-white/50 leading-relaxed max-w-sm ml-auto font-light">
              Because nobody has time to find it.
            </motion.p>
          </motion.div>
        </CinematicOverlay>

        {/* Phase 4 — Frames 121–160 | Scroll 300–400vh */}
        <CinematicOverlay
          active={activePhase === 4}
          scrollYProgress={smoothProgress}
          range={[300 / 1300, 400 / 1300]}
          position="center-bottom"
        >
          <motion.div variants={diagnosticStagger} initial="hidden" animate="show" className="flex flex-col items-center gap-3">
            <motion.div variants={diagnosticItem} className="flex gap-4 font-sans text-[11px] font-semibold text-white/40 uppercase tracking-[0.25em]">
              <span>mETH</span> <span className="text-white/20">·</span> <span>cmETH</span> <span className="text-white/20">·</span> <span>Agni</span>
            </motion.div>
            <motion.div variants={diagnosticItem} className="flex gap-4 font-sans text-[11px] font-semibold text-white/40 uppercase tracking-[0.25em]">
              <span>Merchant Moe</span> <span className="text-white/20">·</span> <span>Ondo USDY</span>
            </motion.div>
            <motion.h3 variants={diagnosticItem} className="text-2xl sm:text-3xl md:text-4xl font-serif text-white/95 leading-snug font-light mt-3 max-w-lg">
              Which one is actually working for you?
            </motion.h3>
          </motion.div>
        </CinematicOverlay>

        {/* Phase 5 — Frames 161–200 | Scroll 400–500vh */}
        <CinematicOverlay
          active={activePhase === 5}
          scrollYProgress={smoothProgress}
          range={[400 / 1300, 500 / 1300]}
          position="bottom-left"
        >
          <FlankingLabel text="Imagine" />
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }} className="flex flex-col gap-2 mt-2">
            <h3 className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light max-w-md">
              What if something intelligent was watching all of it.
            </h3>
            {/* 1.2s Delayed "All the time." */}
            <motion.span
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.2, duration: 1.0, ease: "easeOut" }}
              className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 font-normal block"
            >
              All the time.
            </motion.span>
          </motion.div>
        </CinematicOverlay>

        {/* Phase 6 — Frames 201–240 | Scroll 500–600vh */}
        <CinematicOverlay
          active={activePhase === 6}
          scrollYProgress={smoothProgress}
          range={[500 / 1300, 600 / 1300]}
          position="center"
          fadeInRange={0.25} // glacially slow fade in
        >
          <h2 className="text-4xl sm:text-6xl md:text-7xl font-serif text-white/95 leading-none font-light italic">
            What if yield found you.
          </h2>
        </CinematicOverlay>

        {/* -------------------- TRANSITION BLACKOUT -------------------- */}

        {/* Transition Zone — centred inside the canvas blackout gap (590–710vh) */}
        <CinematicOverlay
          active={activePhase === 7}
          scrollYProgress={smoothProgress}
          range={[615 / 1300, 695 / 1300]}
          position="center"
          fadeInRange={0.2}
          fadeOutRange={0.2}
        >
          <FlankingLabel text="The Answer" slow />
        </CinematicOverlay>

        {/* -------------------- SECTION 2: YIELDSAGE INTRODUCTION OVERLAYS -------------------- */}

        {/* Phase 1 — Frames 1–40 | Scroll 700–800vh */}
        <CinematicOverlay
          active={activePhase === 8}
          scrollYProgress={smoothProgress}
          range={[700 / 1300, 800 / 1300]}
          position="bottom-left"
        >
          <FlankingLabel text="Yield Intelligence" />
          <motion.div variants={staggerContainer} initial="hidden" animate="show" className="flex flex-col gap-2 mt-2">
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light">
              Every protocol.
            </motion.h3>
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light">
              Every opportunity.
            </motion.h3>
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light">
              One intelligence.
            </motion.h3>
          </motion.div>
        </CinematicOverlay>

        {/* Phase 2 — Frames 41–80 | Scroll 800–900vh */}
        <CinematicOverlay
          active={activePhase === 9}
          scrollYProgress={smoothProgress}
          range={[800 / 1300, 900 / 1300]}
          position="bottom-right"
        >
          <FlankingLabel text="Always Watching" />
          <motion.div variants={staggerContainer} initial="hidden" animate="show" className="flex flex-col gap-4 mt-2">
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light max-w-sm ml-auto">
              YieldSage monitors Mantle in real time.
            </motion.h3>
            <motion.p variants={staggerItem} className="text-xs font-sans tracking-[0.35em] text-white/45 uppercase font-semibold">
              Continuously. Autonomously.
            </motion.p>
          </motion.div>
        </CinematicOverlay>

        {/* Phase 3 — Frames 81–120 | Scroll 900–1000vh */}
        <CinematicOverlay
          active={activePhase === 10}
          scrollYProgress={smoothProgress}
          range={[900 / 1300, 1000 / 1300]}
          position="bottom-left"
        >
          <FlankingLabel text="Ranked. Always." />
          <motion.div variants={staggerContainer} initial="hidden" animate="show" className="flex flex-col gap-5 mt-2">
            <motion.h3 variants={staggerItem} className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light max-w-md">
              Every yield opportunity ranked by risk-adjusted return.
            </motion.h3>
            <motion.div variants={staggerItem} className="flex gap-4 font-sans text-[11px] font-bold text-white/40 uppercase tracking-[0.25em]">
              <span>Stable</span> <span className="text-white/20">·</span> <span>Moderate</span> <span className="text-white/20">·</span> <span>Aggressive</span>
            </motion.div>
          </motion.div>
        </CinematicOverlay>

        {/* Phase 4 — Frames 121–160 | Scroll 1000–1100vh */}
        <CinematicOverlay
          active={activePhase === 11}
          scrollYProgress={smoothProgress}
          range={[1000 / 1300, 1100 / 1300]}
          position="center-bottom"
        >
          <FlankingLabel text="On-Chain Verified" />
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }} className="flex flex-col items-center gap-3.5 mt-2">
            <h3 className="text-3xl sm:text-4xl md:text-5xl font-serif text-white/95 leading-tight font-light max-w-lg">
              Every recommendation logged on Mantle.
            </h3>
            <div className="flex flex-col items-center gap-1 font-sans text-xs text-white/50 tracking-wider font-light mt-1">
              <span>Verifiable. Transparent.</span>
              {/* 0.8s Delayed "Yours." */}
              <motion.span
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8, duration: 0.8 }}
                className="font-bold text-white/70 block mt-0.5 tracking-widest uppercase text-[11px]"
              >
                Yours.
              </motion.span>
            </div>
          </motion.div>
        </CinematicOverlay>

        {/* Phase 5 — Frames 161–200 | Scroll 1100–1200vh */}
        <CinematicOverlay
          active={activePhase === 12}
          scrollYProgress={smoothProgress}
          range={[1100 / 1300, 1200 / 1300]}
          position="top-center-high"
        >
          <FlankingLabel text="Meet The Intelligence" slow />
        </CinematicOverlay>

        {/* Phase 6 — Frames 201–240 | Scroll 1200–1300vh (Peak Brand Reveal) */}
        <CinematicOverlay
          active={activePhase === 13}
          scrollYProgress={smoothProgress}
          range={[1200 / 1300, 1.0]}
          position="center-bottom"
          fadeOutRange={0.05} // keep it until very bottom
        >
          <div className="flex flex-col items-center relative py-2">
            
            {/* Subline delayed 0.4s */}
            <motion.p
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 1.0, ease: "easeOut" }}
              className="text-base sm:text-lg md:text-xl font-sans text-white/50 leading-relaxed font-light tracking-wide max-w-md"
            >
              Your autonomous yield intelligence on Mantle.
            </motion.p>

            {/* CTA button delayed 1.0s */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.0, duration: 1.0, ease: [0.22, 1, 0.36, 1] }}
              className="mt-6 z-20 pointer-events-auto"
            >
              <a
                href="#features"
                className="px-8 py-3.5 rounded-full text-xs font-semibold uppercase tracking-[0.2em] font-sans border transition-all duration-300 relative group overflow-hidden block"
                style={{
                  borderColor: "rgba(255,255,255,0.2)",
                  color: "rgba(255,255,255,0.95)",
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLAnchorElement
                  el.style.borderColor = "rgba(0,255,136,0.6)"
                  el.style.color = "rgba(0,255,136,1)"
                  el.style.boxShadow = "0 0 30px rgba(0,255,136,0.25), inset 0 0 10px rgba(0,255,136,0.1)"
                  el.style.background = "rgba(0,255,136,0.02)"
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLAnchorElement
                  el.style.borderColor = "rgba(255,255,255,0.2)"
                  el.style.color = "rgba(255,255,255,0.95)"
                  el.style.boxShadow = "none"
                  el.style.background = "transparent"
                }}
              >
                Enter App →
              </a>
            </motion.div>
          </div>
        </CinematicOverlay>

        {/* -------------------- DECORATION GLOWS & BORDERS -------------------- */}

        {/* Global Cinematic Top & Bottom shadows for blending */}
        <div
          className="absolute inset-x-0 top-0 h-40 pointer-events-none z-20"
          style={{ background: "linear-gradient(to bottom, #050505 0%, transparent 100%)" }}
        />
        <div
          className="absolute inset-x-0 bottom-0 h-40 pointer-events-none z-20"
          style={{ background: "linear-gradient(to top, #050505 0%, transparent 100%)" }}
        />

        {/* Elegant cinematic side vignettes */}
        <div
          className="absolute inset-y-0 left-0 w-32 pointer-events-none z-20 hidden md:block"
          style={{ background: "linear-gradient(to right, #050505 0%, transparent 100%)", opacity: 0.7 }}
        />
        <div
          className="absolute inset-y-0 right-0 w-32 pointer-events-none z-20 hidden md:block"
          style={{ background: "linear-gradient(to left, #050505 0%, transparent 100%)", opacity: 0.7 }}
        />

        {/* Scroll Progress Line (Right Edge) */}
        <motion.div
          className="absolute right-0 top-0 w-[2px] origin-top opacity-30 z-30"
          style={{
            scaleY: smoothProgress,
            background: "linear-gradient(to bottom, transparent, rgba(0,255,136,0.8), transparent)",
            height: "100%",
            transformOrigin: "top",
          }}
        />
      </div>
    </section>
  )
}
