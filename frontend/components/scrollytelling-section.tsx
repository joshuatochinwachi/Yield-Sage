"use client"

import { useRef } from "react"
import { useScroll, useTransform, motion, type MotionValue } from "framer-motion"
import { ScrollCanvas } from "@/components/scroll-canvas"

interface ScrollytellingProps {
  frames: HTMLImageElement[]
}

// Phase 1 (0 - 30) is deep space, no text overlay.
// 240 frames total. 
// Phase 2: 31-80 (0.129 - 0.333)
// Phase 3: 81-130 (0.337 - 0.541)
// Phase 4: 131-180 (0.545 - 0.750)
// Phase 5: 181-240 (0.754 - 1.0)
type Position = "left-center" | "right-center" | "bottom-left" | "bottom-right" | "bottom-center"

const textOverlays: { range: [number, number]; heading: string; position: Position; overline: string }[] = [
  {
    range: [0.129, 0.333],
    overline: "01 // Coverage",
    heading: "Every Yield Opportunity on Mantle",
    position: "left-center"
  },
  {
    range: [0.345, 0.541],
    overline: "02 // Engine",
    heading: "Ranked. Risk-Adjusted. Real-Time.",
    position: "right-center"
  },
  {
    range: [0.55, 0.750],
    overline: "03 // Intelligence",
    heading: "Meet YieldSage",
    position: "bottom-left"
  },
  {
    range: [0.77, 1.0],
    overline: "04 // Autonomy",
    heading: "Your Autonomous Yield Intelligence",
    position: "bottom-right"
  },
]

interface TextOverlayProps {
  scrollYProgress: MotionValue<number>
  heading: string
  range: [number, number]
  position: Position
  overline: string
}

function TextOverlay({ scrollYProgress, heading, range, position, overline }: TextOverlayProps) {
  const midpoint = (range[0] + range[1]) / 2
  const fadeInEnd = range[0] + (midpoint - range[0]) * 0.4
  const fadeOutStart = midpoint + (range[1] - midpoint) * 0.6

  // Parallax + Fade + Blur
  const opacity = useTransform(
    scrollYProgress,
    [range[0], fadeInEnd, fadeOutStart, range[1]],
    [0, 1, 1, 0]
  )
  
  // Custom Y movement based on position to slide in beautifully
  const isTopOrCenter = position.includes("center") && !position.includes("bottom")
  const yOffset = isTopOrCenter ? 30 : 50
  const y = useTransform(
    scrollYProgress,
    [range[0], fadeInEnd, fadeOutStart, range[1]],
    [yOffset, 0, 0, -yOffset]
  )
  
  const scale = useTransform(
    scrollYProgress,
    [range[0], fadeInEnd, fadeOutStart, range[1]],
    [0.95, 1, 1, 1.05]
  )
  const blur = useTransform(
    scrollYProgress,
    [range[0], fadeInEnd, fadeOutStart, range[1]],
    ["blur(12px)", "blur(0px)", "blur(0px)", "blur(12px)"]
  )

  let alignClasses = ""
  let textClasses = ""
  
  switch (position) {
    case "left-center":
      alignClasses = "items-start justify-center pl-8 md:pl-24"
      textClasses = "text-left"
      break
    case "right-center":
      alignClasses = "items-end justify-center pr-8 md:pr-24"
      textClasses = "text-right"
      break
    case "bottom-left":
      alignClasses = "items-start justify-end pb-24 pl-8 md:pl-24"
      textClasses = "text-left"
      break
    case "bottom-right":
      alignClasses = "items-end justify-end pb-24 pr-8 md:pr-24"
      textClasses = "text-right"
      break
    case "bottom-center":
      alignClasses = "items-center justify-end pb-24"
      textClasses = "text-center"
      break
  }

  return (
    <motion.div
      style={{ opacity, y, scale, filter: blur }}
      className={`absolute inset-0 flex flex-col pointer-events-none ${alignClasses}`}
    >
      <div className={`max-w-md ${textClasses}`}>
        {/* Premium Glass HUD Panel */}
        <div 
          className="backdrop-blur-md bg-[#050505]/40 p-8 rounded-2xl relative overflow-hidden"
          style={{
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 20px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)"
          }}
        >
          {/* Subtle accent glow inside panel */}
          <div 
            className="absolute -top-10 -left-10 w-32 h-32 rounded-full pointer-events-none"
            style={{ background: "radial-gradient(circle, rgba(0,255,136,0.15) 0%, transparent 70%)" }}
          />
          
          <div className={`flex flex-col gap-3 relative z-10 ${position.includes('right') ? 'items-end' : position.includes('center') && !position.includes('left') && !position.includes('right') ? 'items-center' : 'items-start'}`}>
            <span className="text-[10px] tracking-[0.3em] font-mono uppercase" style={{ color: "rgba(0,255,136,0.8)" }}>
              {overline}
            </span>
            <h2 className="text-3xl md:text-4xl font-medium tracking-tight text-white/95 leading-snug">
              {heading}
            </h2>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function AmbientParticles({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  // Move particles slowly upwards as you scroll down
  const yOffset = useTransform(scrollYProgress, [0, 1], [0, -200])
  const opacity = useTransform(scrollYProgress, [0, 0.1, 0.9, 1], [0, 1, 1, 0])

  return (
    <motion.div style={{ y: yOffset, opacity }} className="absolute inset-0 pointer-events-none overflow-hidden">
      {[...Array(30)].map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-white/20"
          style={{
            width: Math.random() * 3 + 1 + "px",
            height: Math.random() * 3 + 1 + "px",
            left: Math.random() * 100 + "%",
            top: Math.random() * 100 + "%",
            animation: `float-particle ${Math.random() * 10 + 10}s linear infinite`,
            animationDelay: `-${Math.random() * 10}s`
          }}
        />
      ))}
      <style>{`
        @keyframes float-particle {
          0% { transform: translateY(0) rotate(0deg); opacity: 0; }
          20% { opacity: 0.8; }
          80% { opacity: 0.8; }
          100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
        }
      `}</style>
    </motion.div>
  )
}

export function ScrollytellingSection({ frames }: ScrollytellingProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  })

  // Dynamic glow that pulses during the sequence
  const glowOpacity = useTransform(scrollYProgress, [0, 0.5, 1], [0, 0.15, 0.3])
  const glowScale = useTransform(scrollYProgress, [0, 1], [0.8, 1.2])

  return (
    <section
      ref={containerRef}
      // 400vh gives a very cinematic, slow scroll real-estate
      className="relative"
      style={{ height: "400vh" }}
    >
      {/* Sticky viewport-filling container */}
      <div className="sticky top-0 h-screen w-full overflow-hidden bg-[#050505]">
        
        {/* Dynamic Background Glow synced to scroll */}
        <motion.div
          className="absolute inset-0 pointer-events-none"
          style={{
            opacity: glowOpacity,
            scale: glowScale,
            background: "radial-gradient(circle at center, rgba(0,255,136,0.15) 0%, transparent 60%)",
          }}
        />

        {/* Ambient floating particles */}
        <AmbientParticles scrollYProgress={scrollYProgress} />

        {/* Canvas Layer */}
        <div className="absolute inset-0">
          <ScrollCanvas
            scrollProgress={scrollYProgress}
            isLoaded={frames.length > 0}
            frames={frames}
          />
        </div>

        {/* Top & Bottom Vignettes to blend perfectly with hero/footer */}
        <div
          className="absolute inset-x-0 top-0 h-40 pointer-events-none"
          style={{ background: "linear-gradient(to bottom, #050505 0%, transparent 100%)" }}
        />
        <div
          className="absolute inset-x-0 bottom-0 h-40 pointer-events-none"
          style={{ background: "linear-gradient(to top, #050505 0%, transparent 100%)" }}
        />

        {/* Side Letterboxes for depth focus */}
        <div
          className="absolute inset-0 pointer-events-none hidden lg:block"
          style={{
            background: "linear-gradient(to right, rgba(5,5,5,0.4) 0%, transparent 15%, transparent 85%, rgba(5,5,5,0.4) 100%)",
          }}
        />

        {/* Cinematic Text Overlays */}
        {textOverlays.map((overlay) => (
          <TextOverlay
            key={overlay.heading}
            scrollYProgress={scrollYProgress}
            heading={overlay.heading}
            range={overlay.range}
            position={overlay.position}
            overline={overlay.overline}
          />
        ))}

        {/* Scroll Progress Indicator Line (Right Edge) */}
        <motion.div
          className="absolute right-0 top-0 w-1 origin-top opacity-50"
          style={{
            scaleY: scrollYProgress,
            background: "linear-gradient(to bottom, transparent, rgba(0,255,136,0.8), transparent)",
            height: "100%",
            transformOrigin: "top",
          }}
        />
      </div>
    </section>
  )
}
