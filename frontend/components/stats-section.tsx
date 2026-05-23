"use client"

import { useEffect, useState, useRef } from "react"
import { ShieldCheck, Cpu, Database, Activity } from "lucide-react"

export function StatsSection() {
  const [elapsed, setElapsed] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0 })
  const [acresCount, setAcresCount] = useState(0)
  const [soilSamples, setSoilSamples] = useState(245681)
  const [isVisible, setIsVisible] = useState(false)
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    // Launch date of Yield-Sage SAGE-I processor core
    const launchDate = new Date("2026-01-01T00:00:00Z")

    const updateTimer = () => {
      const now = new Date()
      const diff = now.getTime() - launchDate.getTime()

      const days = Math.floor(diff / (1000 * 60 * 60 * 24))
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((diff % (1000 * 60)) / 1000)

      setElapsed({ days, hours, minutes, seconds })
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.2 },
    )

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (isVisible && acresCount < 12840) {
      const timeout = setTimeout(() => {
        setAcresCount((prev) => Math.min(prev + 240, 12840))
      }, 15)
      return () => clearTimeout(timeout)
    }
  }, [isVisible, acresCount])

  useEffect(() => {
    // Ticking up dynamic soil data analytics count
    const interval = setInterval(() => {
      setSoilSamples((prev) => prev + Math.floor(Math.random() * 3) + 1)
    }, 1500)
    return () => clearInterval(interval)
  }, [])

  const formatNumber = (n: number) => n.toString().padStart(2, "0")

  return (
    <section ref={sectionRef} className="border-t border-b border-border bg-background/30 backdrop-blur-md relative z-10">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {/* Metric 1: System Uptime Timer */}
        <div className="p-6 md:p-8 border-r border-b sm:border-b-0 border-border group hover:bg-emerald-950/10 transition-colors flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Cpu className="w-3.5 h-3.5 text-accent" />
              <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">SYSTEM RUNTIME</p>
            </div>
            <p className="text-xl md:text-2xl font-mono text-foreground group-hover:text-accent transition-colors">
              {formatNumber(elapsed.days)}:{formatNumber(elapsed.hours)}:{formatNumber(elapsed.minutes)}:
              <span className="text-accent">{formatNumber(elapsed.seconds)}</span>
            </p>
          </div>
          <p className="text-[10px] text-muted-foreground/60 font-mono mt-3">SAGE-I CONTINUOUS UPTIME</p>
        </div>

        {/* Metric 2: Acres Tracked */}
        <div className="p-6 md:p-8 border-r border-b sm:border-b-0 lg:border-b-0 border-border group hover:bg-emerald-950/10 transition-colors flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-3.5 h-3.5 text-amber-400" />
              <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">COVERAGE</p>
            </div>
            <p className="text-2xl md:text-3xl font-mono font-bold text-foreground">
              {acresCount.toLocaleString()}<span className="text-accent">+</span>
            </p>
          </div>
          <p className="text-[10px] text-muted-foreground/60 font-mono mt-3">ACTIVE ACERAGE SURVEYED</p>
        </div>

        {/* Metric 3: Soil Samples Ticker */}
        <div className="p-6 md:p-8 border-r border-b lg:border-b-0 border-border group hover:bg-emerald-950/10 transition-colors flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-3.5 h-3.5 text-accent" />
              <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">TELEMETRY INGESTION</p>
            </div>
            <p className="text-xl md:text-2xl font-mono text-foreground">
              {soilSamples.toLocaleString()}
            </p>
          </div>
          <p className="text-[10px] text-muted-foreground/60 font-mono mt-3">CHEMISTRY SENSOR DATA INGESTED</p>
        </div>

        {/* Metric 4: System Status */}
        <div className="p-6 md:p-8 group hover:bg-emerald-950/10 transition-colors flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">PREDICTIVE STABILITY</p>
            </div>
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
              </span>
              <p className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                Yield gain <span className="text-accent font-mono">+32.4%</span>
              </p>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground/60 font-mono mt-3">VERIFIED HARVEST DELTA OUTCOME</p>
        </div>
      </div>
    </section>
  )
}
