"use client"

import { useEffect, useRef } from "react"

export function MouseGradientBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouseRef = useRef({ x: 0.5, y: 0.5 })
  const targetRef = useRef({ x: 0.5, y: 0.5 })
  const timeRef = useRef(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }

    resize()
    window.addEventListener("resize", resize)

    const handleMouseMove = (e: MouseEvent) => {
      targetRef.current = {
        x: e.clientX / window.innerWidth,
        y: e.clientY / window.innerHeight,
      }
    }

    window.addEventListener("mousemove", handleMouseMove)

    let animationId: number

    const animate = () => {
      timeRef.current += 0.015

      // Smooth interpolation for delayed trail physics
      mouseRef.current.x += (targetRef.current.x - mouseRef.current.x) * 0.04
      mouseRef.current.y += (targetRef.current.y - mouseRef.current.y) * 0.04

      const { x, y } = mouseRef.current
      const w = canvas.width
      const h = canvas.height
      const t = timeRef.current

      // Pitch-black background with a slight emerald tint
      ctx.fillStyle = "#030a06"
      ctx.fillRect(0, 0, w, h)

      const pulse = 0.95 + Math.sin(t * 1.8) * 0.05
      const pulse2 = 0.95 + Math.cos(t * 1.2) * 0.05

      // Gradient 1: Sage Green Glow tracking the mouse
      const gradient = ctx.createRadialGradient(x * w, y * h, 0, x * w, y * h, Math.max(w, h) * 0.65)
      gradient.addColorStop(0, `rgba(40, 180, 110, ${0.28 * pulse})`)
      gradient.addColorStop(0.2, `rgba(30, 150, 90, ${0.18 * pulse})`)
      gradient.addColorStop(0.5, `rgba(20, 100, 60, ${0.08 * pulse})`)
      gradient.addColorStop(0.8, `rgba(10, 50, 30, ${0.02 * pulse})`)
      gradient.addColorStop(1, "rgba(3, 10, 6, 0)")

      ctx.fillStyle = gradient
      ctx.fillRect(0, 0, w, h)

      // Gradient 2: Harvest Gold / Amber Glow in counter-balance position
      const gradient2 = ctx.createRadialGradient(
        (1 - x) * w * 0.8 + Math.sin(t) * 40,
        (1 - y) * h * 0.8 + Math.cos(t) * 40,
        0,
        (1 - x) * w * 0.8,
        (1 - y) * h * 0.8,
        Math.max(w, h) * 0.45,
      )
      gradient2.addColorStop(0, `rgba(210, 160, 40, ${0.16 * pulse2})`)
      gradient2.addColorStop(0.3, `rgba(170, 120, 30, ${0.08 * pulse2})`)
      gradient2.addColorStop(0.7, `rgba(100, 70, 10, ${0.02 * pulse2})`)
      gradient2.addColorStop(1, "rgba(3, 10, 6, 0)")

      ctx.fillStyle = gradient2
      ctx.fillRect(0, 0, w, h)

      // Gradient 3: Soft ambient background light pulsating in the center
      const gradient3 = ctx.createRadialGradient(
        w * 0.5 + Math.sin(t * 0.6) * w * 0.25,
        h * 0.5 + Math.cos(t * 0.4) * h * 0.25,
        0,
        w * 0.5,
        h * 0.5,
        Math.max(w, h) * 0.5,
      )
      gradient3.addColorStop(0, `rgba(40, 200, 140, ${0.06 * pulse})`)
      gradient3.addColorStop(0.5, `rgba(25, 120, 80, ${0.02 * pulse})`)
      gradient3.addColorStop(1, "rgba(3, 10, 6, 0)")

      ctx.fillStyle = gradient3
      ctx.fillRect(0, 0, w, h)

      animationId = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      window.removeEventListener("resize", resize)
      window.removeEventListener("mousemove", handleMouseMove)
      cancelAnimationFrame(animationId)
    }
  }, [])

  return (
    <>
      <canvas ref={canvasRef} className="fixed inset-0 z-0 pointer-events-none" style={{ background: "#030a06" }} />

      <div className="fixed inset-0 z-[1] pointer-events-none overflow-hidden opacity-[0.08]">
        {/* Farm plot acreage grid overlay */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)
            `,
            backgroundSize: "80px 80px",
          }}
        />

        {/* Scattered agricultural science and GPS telemetry labels */}
        <div className="absolute top-[8%] left-[6%] font-mono text-[9px] text-emerald-400/80 rotate-[-3deg] space-y-0.5">
          <div>SOIL SENSORS SYNC: SAGE-NET_49B</div>
          <div>MOISTURE PROBE: Active [34.8%]</div>
        </div>

        <div className="absolute top-[14%] right-[8%] font-mono text-[9px] text-amber-400/70 rotate-[2deg] text-right">
          <div>NDVI EQUATION: (NIR - RED) / (NIR + RED)</div>
          <div>NDVI STATUS: OPTIMAL [0.79]</div>
        </div>

        <div className="absolute top-[32%] left-[12%] font-mono text-[8px] text-emerald-300/60 rotate-[-1deg] space-y-1">
          <div>PLOT GEOMETRY coordinates:</div>
          <div>LAT: 42° 21' 36" N | LON: 71° 03' 32" W</div>
          <div>ELEVATION: 142m MSL</div>
        </div>

        <div className="absolute top-[28%] right-[18%] font-mono text-[9px] text-amber-500/60 rotate-[4deg]">
          <div className="border border-amber-500/30 px-2 py-0.5 rounded bg-amber-950/20">PREDICTIVE STAGE</div>
        </div>

        <div className="absolute top-[48%] left-[4%] font-mono text-[9px] text-emerald-400/60 rotate-[5deg] space-y-0.5">
          <div>CHEMISTRY DATA VECTORS:</div>
          <div>NITROGEN (N): 48mg/kg [IDEAL]</div>
          <div>PHOSPHORUS (P): 24mg/kg [SUFFICIENT]</div>
          <div>POTASSIUM (K): 124mg/kg [IDEAL]</div>
        </div>

        <div className="absolute top-[52%] right-[4%] font-mono text-[9px] text-emerald-300/70 rotate-[-2deg] space-y-0.5">
          <div>SAGE-I PROCESSOR LOAD: 12.8%</div>
          <div>EST. YIELD INDEX: +32.4% vs BASELINE</div>
        </div>

        <div className="absolute top-[68%] left-[22%] font-mono text-[8px] text-amber-400/50 rotate-[3deg] space-y-0.5">
          <div>HYBRID SEED MODEL GENETICS:</div>
          <div>VARIETAL: SAGE_ORACLE_V4.2.1</div>
          <div>STRESS ADAPTIVE FACTOR: 98%</div>
        </div>

        <div className="absolute top-[72%] right-[14%] font-mono text-[10px] text-emerald-400/60 rotate-[-4deg] flex items-center gap-1.5">
          <div className="text-[20px] leading-none text-emerald-500">⬡</div>
          <div>CLIMATE RESILIENT INTEGRITY</div>
        </div>

        <div className="absolute bottom-[10%] left-[8%] font-mono text-[8px] text-emerald-300/55 rotate-[6deg] space-y-0.5">
          <div>||| |||| ||| |||| |||</div>
          <div>SCAN SOIL FOR TELEMETRY</div>
        </div>

        <div className="absolute bottom-[12%] right-[6%] font-mono text-[8px] text-amber-400/65 rotate-[-3deg] text-right">
          <div>SYSTEM TELEMETRY ENGINE: ACTIVE</div>
          <div>MODEL REF: YIELD_SAGE_MODEL_092</div>
        </div>

        {/* Circular Verified Badges in Background */}
        <div className="absolute top-[22%] left-[44%] w-20 h-20 border-2 border-emerald-500/20 rounded-full flex items-center justify-center rotate-[-12deg]">
          <div className="text-[7px] text-emerald-400/50 text-center font-mono leading-tight">
            <div>COGNITIVE</div>
            <div>ADVISORY</div>
            <div className="font-bold text-[8px] mt-0.5">SAGE-I</div>
          </div>
        </div>

        <div className="absolute bottom-[24%] left-[40%] w-16 h-16 border border-dashed border-amber-500/25 rounded flex items-center justify-center rotate-[18deg]">
          <div className="text-[6px] text-amber-400/60 font-mono text-center leading-tight">
            <div>ORGANIC</div>
            <div>COMPILING</div>
            <div>✓ VERIFIED</div>
          </div>
        </div>
      </div>

      {/* Luxury cinema-grade noise grain overlay */}
      <div
        className="fixed inset-0 z-[2] pointer-events-none opacity-[0.02]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          backgroundRepeat: "repeat",
        }}
      />
    </>
  )
}
