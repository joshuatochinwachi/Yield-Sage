"use client"

import { useState, useCallback } from "react"
import { LoadingScreen } from "@/components/loading-screen"
import { HeroSection } from "@/components/hero-section"
import { ScrollytellingSection } from "@/components/scrollytelling-section"
import { FeaturesSection } from "@/components/features-section"
import { Footer } from "@/components/footer"

export default function Home() {
  const [frames, setFrames] = useState<HTMLImageElement[]>([])
  const [isReady, setIsReady] = useState(false)

  const handleLoadComplete = useCallback((loadedFrames: HTMLImageElement[]) => {
    setFrames(loadedFrames)
    setIsReady(true)
  }, [])

  return (
    <>
      {/* Frame preloader — shown until all 240 images are in memory */}
      {!isReady && <LoadingScreen onComplete={handleLoadComplete} />}

      {/* Main page — fades in after load */}
      <main
        id="sequence"
        style={{
          opacity: isReady ? 1 : 0,
          transition: "opacity 0.8s ease",
          background: "#050505",
          minHeight: "100vh",
        }}
      >
        {/* 1. Minimal cinematic hero intro */}
        <HeroSection />

        {/* 2. Scroll-controlled image sequence — 300vh sticky */}
        <ScrollytellingSection frames={frames} />

        {/* 3. Feature cards */}
        <FeaturesSection />

        {/* 4. CTA + footer */}
        <Footer />
      </main>
    </>
  )
}
