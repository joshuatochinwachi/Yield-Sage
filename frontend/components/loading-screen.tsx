"use client"

import { useEffect, useState, useRef } from "react"

interface LoadingScreenProps {
  onComplete: (frames: HTMLImageElement[]) => void
}

const TOTAL_FRAMES = 240

export function LoadingScreen({ onComplete }: LoadingScreenProps) {
  const [progress, setProgress] = useState(0)
  const [phase, setPhase] = useState<"loading" | "done" | "exit">("loading")
  const framesRef = useRef<HTMLImageElement[]>([])
  const hasCalledComplete = useRef(false)

  useEffect(() => {
    let loadedCount = 0
    const frames: HTMLImageElement[] = new Array(TOTAL_FRAMES)

    const loadFrame = (index: number): Promise<void> => {
      return new Promise((resolve) => {
        const img = new Image()
        const frameNum = String(index + 1).padStart(3, "0")
        img.src = `/hero-sequence/ezgif-frame-${frameNum}.jpg`
        img.onload = () => {
          frames[index] = img
          loadedCount++
          setProgress(Math.round((loadedCount / TOTAL_FRAMES) * 100))
          resolve()
        }
        img.onerror = () => {
          // Still count failed frames so loading can complete
          loadedCount++
          setProgress(Math.round((loadedCount / TOTAL_FRAMES) * 100))
          resolve()
        }
      })
    }

    // Load in batches of 20 for optimal memory / speed balance
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
        }, 300)
      }
    }

    loadInBatches()
  }, [onComplete])

  if (phase === "exit") return null

  return (
    <div
      className="fixed inset-0 z-[200] flex flex-col items-center justify-center"
      style={{
        background: "#050505",
        opacity: phase === "done" ? 0 : 1,
        transition: "opacity 0.7s ease",
        pointerEvents: phase === "done" ? "none" : "all",
      }}
    >
      {/* Subtle ambient glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0,255,136,0.04) 0%, transparent 70%)",
        }}
      />

      <div className="relative z-10 flex flex-col items-center gap-10 w-full max-w-xs px-8">
        {/* Wordmark */}
        <div className="text-center">
          <p className="text-[10px] tracking-[0.4em] text-white/30 uppercase font-mono mb-3">
            Initializing
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-white/90">
            YieldSage
          </h1>
        </div>

        {/* Progress bar track */}
        <div className="w-full flex flex-col gap-3">
          <div className="w-full h-px bg-white/10 relative overflow-hidden rounded-full">
            <div
              className="absolute inset-y-0 left-0 rounded-full transition-all duration-150 ease-out"
              style={{
                width: `${progress}%`,
                background:
                  "linear-gradient(90deg, rgba(0,255,136,0.6) 0%, rgba(0,255,136,1) 100%)",
                boxShadow: "0 0 8px rgba(0,255,136,0.8)",
              }}
            />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-white/25 tracking-widest uppercase">
              Loading assets
            </span>
            <span
              className="text-[11px] font-mono font-medium tabular-nums"
              style={{ color: "rgba(0,255,136,0.9)" }}
            >
              {progress}%
            </span>
          </div>
        </div>

        {/* Pulsing dot indicators */}
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1 h-1 rounded-full bg-white/20"
              style={{
                animation: `pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
                backgroundColor:
                  progress > (i + 1) * 33
                    ? "rgba(0,255,136,0.8)"
                    : "rgba(255,255,255,0.15)",
              }}
            />
          ))}
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.5); }
        }
      `}</style>
    </div>
  )
}
