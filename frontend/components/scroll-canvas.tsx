"use client"

import { useEffect, useRef, useCallback } from "react"
import { useSpring, useTransform, type MotionValue } from "framer-motion"

const TOTAL_FRAMES = 240

interface ScrollCanvasProps {
  scrollProgress: MotionValue<number>
  isLoaded: boolean
  frames: HTMLImageElement[]
}

export function ScrollCanvas({ scrollProgress, isLoaded, frames }: ScrollCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef = useRef<number | null>(null)
  const lastFrameRef = useRef<number>(-1)

  // Spring-smoothed scroll value for cinematic inertia feel
  const smoothProgress = useSpring(scrollProgress, {
    stiffness: 50,
    damping: 20,
    restDelta: 0.0005,
  })

  // Map 0→1 progress to frame index 0→(TOTAL_FRAMES-1)
  const frameIndex = useTransform(smoothProgress, [0, 1], [0, TOTAL_FRAMES - 1])

  const drawFrame = useCallback(
    (index: number) => {
      const canvas = canvasRef.current
      if (!canvas || !isLoaded || frames.length === 0) return

      const clampedIndex = Math.round(Math.min(Math.max(index, 0), TOTAL_FRAMES - 1))

      // Skip draw if same frame
      if (clampedIndex === lastFrameRef.current) return
      lastFrameRef.current = clampedIndex

      const ctx = canvas.getContext("2d", { alpha: false })
      if (!ctx) return
      
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = "high"

      const img = frames[clampedIndex]
      if (!img || !img.complete || img.naturalWidth === 0) return

      // High-DPI / Retina support
      const dpr = window.devicePixelRatio || 1
      const w = canvas.offsetWidth
      const h = canvas.offsetHeight

      // Only resize canvas if dimensions changed
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr
        canvas.height = h * dpr
        ctx.scale(dpr, dpr)
      }

      // Object-fit: cover math — maintains aspect ratio and fills canvas
      const imgAspect = img.naturalWidth / img.naturalHeight
      const canvasAspect = w / h

      let drawW: number, drawH: number, drawX: number, drawY: number

      if (imgAspect > canvasAspect) {
        // Image is wider than canvas: fit height, clip width
        drawH = h
        drawW = h * imgAspect
        drawX = (w - drawW) / 2
        drawY = 0
      } else {
        // Image is taller than canvas: fit width, clip height
        drawW = w
        drawH = w / imgAspect
        drawX = 0
        drawY = (h - drawH) / 2
      }

      ctx.clearRect(0, 0, w, h)
      ctx.drawImage(img, drawX, drawY, drawW, drawH)
    },
    [isLoaded, frames]
  )

  // Subscribe to frameIndex motion value and schedule RAF draws
  useEffect(() => {
    const unsubscribe = frameIndex.on("change", (latest) => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      rafRef.current = requestAnimationFrame(() => drawFrame(latest))
    })

    return () => {
      unsubscribe()
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [frameIndex, drawFrame])

  // Handle window resize — redraw current frame at new dimensions
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current
      if (!canvas) return
      // Reset cached dims so next draw recomputes
      canvas.width = 0
      canvas.height = 0
      drawFrame(lastFrameRef.current)
    }
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [drawFrame])

  // Draw first frame when loaded
  useEffect(() => {
    if (isLoaded && frames.length > 0) {
      drawFrame(0)
    }
  }, [isLoaded, frames, drawFrame])

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full block"
      style={{ display: "block" }}
      aria-hidden="true"
    />
  )
}
