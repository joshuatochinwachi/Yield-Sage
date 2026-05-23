"use client"

import { useEffect, useRef, useCallback } from "react"
import { type MotionValue } from "framer-motion"

const TOTAL_FRAMES = 240
// Section 1 ends at 590vh (10vh earlier — gives canvasOpacity time to fade to 0 FIRST)
const SECTION_1_CUTOFF = 590 / 1300
// Section 2 begins at 710vh (10vh later — canvas is fully opaque again before drawing)
const SECTION_2_START = 710 / 1300

interface ScrollCanvasProps {
  scrollProgress: MotionValue<number>
  section1Frames: HTMLImageElement[]
  section2Frames: HTMLImageElement[]
}

export function ScrollCanvas({ scrollProgress, section1Frames, section2Frames }: ScrollCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef = useRef<number | null>(null)
  
  const lastFrameIndexRef = useRef<number>(-1)
  const lastSectionRef = useRef<number>(-1)

  const drawFrame = useCallback(
    (latestProgress: number) => {
      const canvas = canvasRef.current
      if (!canvas) return

      const ctx = canvas.getContext("2d", { alpha: false })
      if (!ctx) return

      let activeFrames = section1Frames
      let p = 0
      let section = 1

      if (latestProgress <= SECTION_1_CUTOFF) {
        // Section 1 — frames 1..240 mapped from 0..SECTION_1_CUTOFF
        p = latestProgress / SECTION_1_CUTOFF
        activeFrames = section1Frames
        section = 1
      } else if (latestProgress >= SECTION_2_START) {
        // Section 2 — frames 1..240 mapped from SECTION_2_START..1.0
        p = (latestProgress - SECTION_2_START) / (1 - SECTION_2_START)
        activeFrames = section2Frames
        section = 2
      } else {
        // Transition blackout zone — clear the canvas to the same background colour
        // so absolutely no image data leaks through at any point during the canvas
        // opacity animation in scrollytelling-section.tsx.
        ctx.fillStyle = "#050505"
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        lastFrameIndexRef.current = -1
        lastSectionRef.current = -1
        return
      }

      if (activeFrames.length === 0) return

      const targetIndex = Math.round(Math.min(Math.max(p * (TOTAL_FRAMES - 1), 0), TOTAL_FRAMES - 1))

      let clampedIndex = targetIndex
      let img = activeFrames[clampedIndex]

      // Fallback: if target frame isn't loaded yet, scan backwards for the nearest loaded frame
      while ((!img || !img.complete || img.naturalWidth === 0) && clampedIndex > 0) {
        clampedIndex--
        img = activeFrames[clampedIndex]
      }

      if (!img || !img.complete || img.naturalWidth === 0) return

      // Skip draw if we're going to draw the exact same image and section as last time
      if (clampedIndex === lastFrameIndexRef.current && section === lastSectionRef.current) return
      
      lastFrameIndexRef.current = clampedIndex
      lastSectionRef.current = section

      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = "high"

      const dpr = window.devicePixelRatio || 1
      const w = canvas.offsetWidth
      const h = canvas.offsetHeight

      // Handle resize only when dimensions actually change
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr
        canvas.height = h * dpr
        ctx.scale(dpr, dpr)
      }

      // Aspect-ratio cover calculation
      const imgAspect = img.naturalWidth / img.naturalHeight
      const canvasAspect = w / h

      let drawW: number, drawH: number, drawX: number, drawY: number

      if (imgAspect > canvasAspect) {
        drawH = h
        drawW = h * imgAspect
        drawX = (w - drawW) / 2
        drawY = 0
      } else {
        drawW = w
        drawH = w / imgAspect
        drawX = 0
        drawY = (h - drawH) / 2
      }

      ctx.clearRect(0, 0, w, h)
      ctx.drawImage(img, drawX, drawY, drawW, drawH)
    },
    [section1Frames, section2Frames]
  )

  // Subscribe to pre-smoothed progress and schedule RAF drawings
  useEffect(() => {
    const unsubscribe = scrollProgress.on("change", (latest) => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      rafRef.current = requestAnimationFrame(() => drawFrame(latest))
    })

    return () => {
      unsubscribe()
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [scrollProgress, drawFrame])

  // Window resize handler
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current
      if (!canvas) return
      canvas.width = 0
      canvas.height = 0
      lastFrameIndexRef.current = -1
      drawFrame(scrollProgress.get())
    }
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [drawFrame, scrollProgress])

  // Draw current frame once loaded, and re-draw when new background frames arrive
  useEffect(() => {
    if (section1Frames.length > 0) {
      lastFrameIndexRef.current = -1 // Force redraw check
      drawFrame(scrollProgress.get())
    }
  }, [section1Frames, section2Frames, drawFrame, scrollProgress])

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full block"
      style={{ display: "block" }}
      aria-hidden="true"
    />
  )
}
