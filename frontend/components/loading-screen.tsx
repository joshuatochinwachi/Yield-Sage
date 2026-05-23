"use client"

import { useEffect, useState, useRef } from "react"
import NextImage from "next/image"

interface LoadingScreenProps {
  onComplete: (frames: HTMLImageElement[]) => void
}

const TOTAL_FRAMES = 180

export function LoadingScreen({ onComplete }: LoadingScreenProps) {
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState<"loading" | "done" | "exit">("loading")
  const [glitchText, setGlitchText] = useState("YIELDSAGE")
  const framesRef = useRef<HTMLImageElement[]>([])
  const hasCalledComplete = useRef(false)

  // Character scramble scramble system settled character-by-character
  useEffect(() => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*"
    const target = "YIELDSAGE"
    let frame = 0
    const maxFrames = 25

    const glitchInterval = setInterval(() => {
      if (frame < maxFrames) {
        const newText = target
          .split("")
          .map((char, i) => {
            if (char === " ") return " "
            // The probability of displaying the correct char increases over time
            const probability = frame / maxFrames
            if (Math.random() < probability) return char
            return chars[Math.floor(Math.random() * chars.length)]
          })
          .join("")
        setGlitchText(newText)
        frame++
      } else {
        setGlitchText(target)
        clearInterval(glitchInterval)
      }
    }, 60)

    return () => clearInterval(glitchInterval)
  }, [])

  // Actual frame loading preloader
  useEffect(() => {
    let loadedCount = 0
    const frames: HTMLImageElement[] = new Array(TOTAL_FRAMES)

    const loadFrame = (index: number): Promise<void> => {
      return new Promise((resolve) => {
        const img = new Image()
        const frameNum = String(index + 1).padStart(3, "0")
        img.src = `/frames/ezgif-frame-${frameNum}.jpg`
        img.onload = () => {
          frames[index] = img
          loadedCount++
          setProgress(Math.round((loadedCount / TOTAL_FRAMES) * 100))
          resolve()
        }
        img.onerror = () => {
          // Still count failed frames to avoid blocking the loader
          loadedCount++
          setProgress(Math.round((loadedCount / TOTAL_FRAMES) * 100))
          resolve()
        }
      })
    }

    // Load in batches of 20 for optimized browser request pipelines
    const loadInBatches = async () => {
      const BATCH_SIZE = 20
      for (let i = 0; i < TOTAL_FRAMES; i += BATCH_SIZE) {
        const batch = []
        for (let j = i; j < Math.min(i + BATCH_SIZE, TOTAL_FRAMES); j++) {
          batch.push(loadFrame(j))
        }
        await Promise.all(batch)
      }

      framesRef.current = frames

      if (!hasCalledComplete.current) {
        hasCalledComplete.current = true
        setPhase("done")
        setTimeout(() => {
          setPhase("exit")
          setTimeout(() => onComplete(frames), 700)
        }, 400)
      }
    }

    loadInBatches()
  }, [onComplete])

  if (phase === "exit") return null

  return (
    <div
      className={`fixed inset-0 z-[200] flex flex-col items-center justify-center transition-all duration-700 ${
        phase === "done" ? "opacity-0 scale-105" : "opacity-100 scale-100"
      }`}
      style={{
        background: "#050505",
        pointerEvents: phase === "done" ? "none" : "all",
      }}
    >
      {/* Premium animated background grid */}
      <div className="absolute inset-0 overflow-hidden opacity-20 pointer-events-none">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0,255,136,0.06) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0,255,136,0.06) 1px, transparent 1px)
            `,
            backgroundSize: "40px 40px",
            animation: "gridMove 20s linear infinite",
          }}
        />
      </div>

      {/* Horizontal sweeping lasers */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-10">
        <div
          className="absolute w-full h-[2px]"
          style={{
            top: `${(progress * 0.8 + 10) % 100}%`,
            background: "rgba(0,255,136,0.6)",
            boxShadow: "0 0 15px rgba(0,255,136,0.8), 0 0 35px rgba(0,255,136,0.4)",
            transition: "top 0.15s linear",
          }}
        />
        <div
          className="absolute w-full h-[1px]"
          style={{
            top: `${(progress * 1.1 + 35) % 100}%`,
            background: "rgba(0,255,136,0.3)",
            transition: "top 0.15s linear",
          }}
        />
      </div>

      {/* Center Console Content */}
      <div className="relative z-20 flex flex-col items-center">
        
        {/* Core Product Logo block with laser scan sweep */}
        <div className="relative mb-8 select-none">
          <div
            className="w-20 h-20 border-2 rounded-xl flex items-center justify-center relative overflow-hidden"
            style={{
              borderColor: "rgba(0,255,136,0.35)",
              boxShadow: "0 0 30px rgba(0,255,136,0.15), inset 0 0 15px rgba(0,255,136,0.1)",
            }}
          >
            {/* Moving scan-line light inside logo */}
            <div
              className="absolute inset-0 bg-gradient-to-b from-transparent via-[rgba(0,255,136,0.25)] to-transparent"
              style={{
                transform: `translateY(${(progress * 2) % 200 - 100}%)`,
                transition: "transform 0.1s linear",
              }}
            />
            <NextImage
              src="/logo.jpg"
              alt="YieldSage"
              width={56}
              height={56}
              className="relative z-10 object-cover rounded-lg"
            />
          </div>

          {/* Dual Orbiting glowing dots */}
          <div
            className="absolute -inset-4"
            style={{ animation: "spin 3.5s linear infinite" }}
          >
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-[rgba(0,255,136,0.95)] rounded-full shadow-[0_0_8px_rgba(0,255,136,0.8)]" />
          </div>
          <div
            className="absolute -inset-6"
            style={{ animation: "spin 4.5s linear infinite reverse" }}
          >
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 bg-[rgba(0,255,136,0.4)] rounded-full" />
          </div>
        </div>

        {/* Dynamic character arrangement text */}
        <h1 className="text-2xl md:text-3xl font-mono font-bold tracking-[0.3em] mb-6 text-white/95 uppercase select-none">
          {glitchText}
        </h1>

        {/* Progress bar tracks actual loading percentage */}
        <div className="w-64 md:w-80 h-[2px] bg-white/10 rounded-full overflow-hidden mb-4 relative z-10">
          <div
            className="h-full transition-all duration-150 ease-out relative"
            style={{ 
              width: `${progress}%`,
              background: "linear-gradient(90deg, rgba(0,255,136,0.6) 0%, rgba(0,255,136,1) 100%)",
              boxShadow: "0 0 8px rgba(0,255,136,0.8)"
            }}
          >
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-[rgba(0,255,136,1)] rounded-full animate-ping" />
          </div>
        </div>

        {/* Eased status readouts */}
        <div className="flex items-center gap-4 text-xs font-mono text-white/30 tracking-widest select-none">
          <span>INITIALIZING SYSTEMS</span>
          <span style={{ color: "rgba(0,255,136,0.9)" }} className="font-bold tabular-nums">
            {progress}%
          </span>
        </div>

        {/* Console status indicator grid */}
        <div className="mt-8 flex gap-6 text-[10px] font-mono text-white/20 select-none">
          <div className={`flex items-center gap-2 transition-colors duration-300 ${progress > 25 ? "text-[rgba(0,255,136,0.85)] font-semibold" : ""}`}>
            <span className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${progress > 25 ? "bg-[rgba(0,255,136,0.85)] shadow-[0_0_6px_rgba(0,255,136,0.6)]" : "bg-white/10"}`} />
            CORE
          </div>
          <div className={`flex items-center gap-2 transition-colors duration-300 ${progress > 50 ? "text-[rgba(0,255,136,0.85)] font-semibold" : ""}`}>
            <span className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${progress > 50 ? "bg-[rgba(0,255,136,0.85)] shadow-[0_0_6px_rgba(0,255,136,0.6)]" : "bg-white/10"}`} />
            DATA
          </div>
          <div className={`flex items-center gap-2 transition-colors duration-300 ${progress > 75 ? "text-[rgba(0,255,136,0.85)] font-semibold" : ""}`}>
            <span className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${progress > 75 ? "bg-[rgba(0,255,136,0.85)] shadow-[0_0_6px_rgba(0,255,136,0.6)]" : "bg-white/10"}`} />
            RENDER
          </div>
          <div className={`flex items-center gap-2 transition-colors duration-300 ${progress >= 100 ? "text-[rgba(0,255,136,0.85)] font-semibold" : ""}`}>
            <span className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${progress >= 100 ? "bg-[rgba(0,255,136,0.85)] shadow-[0_0_6px_rgba(0,255,136,0.6)]" : "bg-white/10"}`} />
            READY
          </div>
        </div>
      </div>

      {/* Futuristic technical corners */}
      <div className="absolute top-6 left-6 text-[10px] font-mono text-white/20 select-none">
        <div>SYS.INIT</div>
        <div>v2.1.0</div>
      </div>
      <div className="absolute top-6 right-6 text-[10px] font-mono text-white/20 text-right select-none">
        <div>PLATFORM</div>
        <div>2026</div>
      </div>
      <div className="absolute bottom-6 left-6 text-[10px] font-mono text-white/20 select-none">
        <div>||||||||||||||||</div>
        <div>YS-WP-002</div>
      </div>
      <div className="absolute bottom-6 right-6 text-[10px] font-mono text-white/20 text-right select-none">
        <div>SECURE</div>
        <div>ENCRYPTED</div>
      </div>

      <style>{`
        @keyframes gridMove {
          0% { transform: translate(0, 0); }
          100% { transform: translate(40px, 40px); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
