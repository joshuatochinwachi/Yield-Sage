"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { LoadingScreen } from "@/components/loading-screen"
import { MouseGradientBackground } from "@/components/mouse-gradient-background"
import { ScrollytellingSection } from "@/components/scrollytelling-section"
import { FeaturesSection } from "@/components/features-section"
import { Footer } from "@/components/footer"

export default function Home() {
  const [section1Frames, setSection1Frames] = useState<HTMLImageElement[]>([])
  const [section2Frames, setSection2Frames] = useState<HTMLImageElement[]>([])
  const [isReady, setIsReady] = useState(false)
  const isPreloadingSection2 = useRef(false)
  const isPreloadingRestOfSection1 = useRef(false)

  const preloadRestOfSection1 = useCallback(async (initialFrames: HTMLImageElement[]) => {
    if (isPreloadingRestOfSection1.current) return
    isPreloadingRestOfSection1.current = true
    console.log("Background preloading of remaining Section 1 frames started...")

    const frames: HTMLImageElement[] = [...initialFrames]
    frames.length = 240 // Ensure array size is exactly 240
    const BATCH_SIZE = 20

    const loadFrame = (index: number): Promise<void> => {
      return new Promise((resolve) => {
        if (frames[index]) {
          resolve() // Already loaded from initial batch
          return
        }
        const img = new Image()
        const frameNum = String(index + 1).padStart(3, "0")
        img.src = `/frames/ezgif-frame-${frameNum}.jpg`
        img.onload = () => {
          frames[index] = img
          resolve()
        }
        img.onerror = () => {
          resolve()
        }
      })
    }

    // Load in batches starting from frame 120
    for (let i = 120; i < 240; i += BATCH_SIZE) {
      const batch = []
      for (let j = i; j < Math.min(i + BATCH_SIZE, 240); j++) {
        batch.push(loadFrame(j))
      }
      await Promise.all(batch)
      // Update state incrementally so canvas can use new frames as they arrive
      setSection1Frames([...frames])
    }

    console.log("Remaining Section 1 frames loaded in background!")
  }, [])

  const handleLoadComplete = useCallback((loadedFrames: HTMLImageElement[]) => {
    setSection1Frames(loadedFrames)
    setIsReady(true)
    preloadRestOfSection1(loadedFrames)
  }, [preloadRestOfSection1])

  const preloadSection2 = useCallback(async () => {
    if (isPreloadingSection2.current || section2Frames.length > 0) return
    isPreloadingSection2.current = true
    console.log("Background preloading of Section 2 frames started...")
    
    const frames: HTMLImageElement[] = new Array(240)
    const BATCH_SIZE = 20
    
    const loadFrame = (index: number): Promise<void> => {
      return new Promise((resolve) => {
        const img = new Image()
        const frameNum = String(index + 1).padStart(3, "0")
        img.src = `/hero-sequence/ezgif-frame-${frameNum}.jpg`
        img.onload = () => {
          frames[index] = img
          resolve()
        }
        img.onerror = () => {
          resolve()
        }
      })
    }

    // Load in batches of 20
    for (let i = 0; i < 240; i += BATCH_SIZE) {
      const batch = []
      for (let j = i; j < Math.min(i + BATCH_SIZE, 240); j++) {
        batch.push(loadFrame(j))
      }
      await Promise.all(batch)
    }
    
    setSection2Frames(frames)
    console.log("Section 2 frames loaded in background!")
  }, [section2Frames.length])

  // Start preloading Section 2 frames immediately after loading screen finishes
  useEffect(() => {
    if (isReady) {
      preloadSection2()
    }
  }, [isReady, preloadSection2])

  return (
    <>
      {/* Preloader — preloads the 240 Section 1 frames */}
      {!isReady && <LoadingScreen onComplete={handleLoadComplete} />}

      {/* Dynamic, interactive mouse-following glow background (visible in non-scrollytelling sections) */}
      <MouseGradientBackground />

      {/* Main page — visible after Section 1 preloads */}
      <main
        id="sequence"
        style={{
          opacity: isReady ? 1 : 0,
          transition: "opacity 0.8s ease",
          background: "transparent",
          minHeight: "100vh",
        }}
      >
        {/* Scrollytelling Section — starts immediately when the page opens */}
        <ScrollytellingSection 
          section1Frames={section1Frames} 
          section2Frames={section2Frames} 
          preloadSection2={preloadSection2}
        />

        {/* Feature Grid cards */}
        <FeaturesSection />

        {/* Brand reveal footer */}
        <Footer />
      </main>
    </>
  )
}
