"use client"

import { useState, useEffect, useRef } from "react"
import Image from "next/image"

const SESSION_KEY = "hollowscan_promo_dismissed"
const APPEAR_DELAY_MS = 6000

type Phase = "hidden" | "mini" | "expanded" | "gone"

export function HollowScanPromo() {
  const [phase, setPhase] = useState<Phase>("hidden")
  const initialTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const dismissedRef = useRef(false)

  // Check session-storage dismissal on mount
  useEffect(() => {
    if (typeof window !== "undefined" && sessionStorage.getItem(SESSION_KEY) === "true") {
      dismissedRef.current = true
      setPhase("gone")
    }
  }, [])

  // Show mini pill after delay — nothing else opens the card automatically
  useEffect(() => {
    if (dismissedRef.current) return
    initialTimerRef.current = setTimeout(() => {
      setPhase((prev) => (prev === "hidden" ? "mini" : prev))
    }, APPEAR_DELAY_MS)
    return () => { if (initialTimerRef.current) clearTimeout(initialTimerRef.current) }
  }, [])

  const dismiss = () => {
    sessionStorage.setItem(SESSION_KEY, "true")
    dismissedRef.current = true
    setPhase("gone")
  }

  const explore = () => {
    window.open("https://www.hollowscan.com/#hollowscan-section", "_blank", "noopener,noreferrer")
  }

  if (phase === "gone") return null

  const miniVisible = phase === "mini"
  const expandedVisible = phase === "expanded"

  return (
    <>
      {/* ── Keyframe animations ── */}
      <style>{`
        @keyframes hs-glow-pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }
        .hs-explore-btn:hover {
          transform: translateY(-2px) scale(1.02) !important;
          box-shadow: 0 10px 36px rgba(0,220,100,0.55) !important;
        }
        .hs-hide-btn:hover {
          background: rgba(255,255,255,0.1) !important;
          color: rgba(255,255,255,0.9) !important;
        }
        .hs-close-btn:hover {
          background: rgba(220,60,60,0.25) !important;
          border-color: rgba(220,60,60,0.4) !important;
          color: #fff !important;
        }
        .hs-mini-card:hover {
          border-color: rgba(0,220,100,0.28) !important;
          box-shadow: 0 8px 40px rgba(0,0,0,0.65), 0 0 0 1px rgba(0,200,100,0.28), 0 0 22px rgba(0,200,100,0.1) !important;
          transform: translateY(-2px);
        }
      `}</style>

      {/* ─────────────── MINI PILL ─────────────── */}
      <div
        role="complementary"
        aria-label="HollowScan promotion"
        style={{
          position: "fixed",
          bottom: "32px",
          left: "24px",
          zIndex: 9998,
          transform: miniVisible ? "translateX(0)" : "translateX(-130%)",
          opacity: miniVisible ? 1 : 0,
          transition: "transform 0.55s cubic-bezier(0.34,1.56,0.64,1), opacity 0.4s ease",
          pointerEvents: miniVisible ? "auto" : "none",
        }}
      >
        <div
          className="hs-mini-card"
          onClick={() => setPhase("expanded")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            background: "rgba(7, 9, 14, 0.94)",
            border: "1px solid rgba(255,255,255,0.09)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            borderRadius: "16px",
            padding: "10px 14px 10px 10px",
            cursor: "pointer",
            boxShadow: "0 8px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(0,200,100,0.1)",
            maxWidth: "300px",
            userSelect: "none",
            transition: "transform 0.25s ease, border-color 0.25s, box-shadow 0.25s",
          }}
        >
          {/* App icon */}
          <div style={{
            width: "44px", height: "44px",
            borderRadius: "10px", overflow: "hidden",
            flexShrink: 0, border: "1px solid rgba(255,255,255,0.07)",
            position: "relative",
          }}>
            <Image src="/hollowscan_image.png" alt="HollowScan" fill style={{ objectFit: "cover" }} sizes="44px" />
          </div>

          {/* Text */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{
              color: "rgba(255,255,255,0.95)", fontWeight: 700, fontSize: "12px",
              lineHeight: 1.25, margin: 0, whiteSpace: "nowrap",
              overflow: "hidden", textOverflow: "ellipsis",
            }}>
              £5 reward waiting 🎁
            </p>
            <p style={{
              color: "rgba(255,255,255,0.45)", fontSize: "11px", margin: "2px 0 0",
              lineHeight: 1.35, overflow: "hidden", display: "-webkit-box",
              WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const,
            }}>
              Never miss a resale flip again.
            </p>
          </div>

          {/* Close X */}
          <button
            className="hs-close-btn"
            aria-label="Dismiss promotion"
            onClick={(e) => { e.stopPropagation(); dismiss() }}
            style={{
              background: "transparent", border: "1px solid transparent",
              color: "rgba(255,255,255,0.3)", cursor: "pointer",
              padding: 0, width: "22px", height: "22px",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "17px", lineHeight: 1, borderRadius: "50%",
              flexShrink: 0, transition: "all 0.2s",
            }}
          >×</button>
        </div>
      </div>

      {/* ─────────────── EXPANDED CARD ─────────────── */}
      <div
        style={{
          position: "fixed",
          bottom: "32px",
          left: "24px",
          zIndex: 9999,
          width: "min(360px, calc(100vw - 48px))",
          maxHeight: "calc(100vh - 48px)",
          transform: expandedVisible ? "translateY(0) scale(1)" : "translateY(22px) scale(0.93)",
          opacity: expandedVisible ? 1 : 0,
          pointerEvents: expandedVisible ? "auto" : "none",
          transition: "transform 0.5s cubic-bezier(0.34,1.4,0.64,1), opacity 0.35s ease",
        }}
      >
        {/* Animated glow border */}
        <div style={{
          position: "absolute", inset: "-1px", borderRadius: "21px",
          background: "linear-gradient(135deg, rgba(0,220,100,0.36) 0%, rgba(0,180,255,0.15) 60%, transparent 100%)",
          zIndex: -1,
          animation: expandedVisible ? "hs-glow-pulse 2.8s ease-in-out infinite" : "none",
        }} />

        {/* Card */}
        <div style={{
          background: "rgba(6, 8, 12, 0.98)",
          borderRadius: "20px",
          border: "1px solid rgba(255,255,255,0.07)",
          backdropFilter: "blur(40px)",
          WebkitBackdropFilter: "blur(40px)",
          overflow: "hidden",
          boxShadow: "0 32px 80px rgba(0,0,0,0.85), 0 0 60px rgba(0,200,100,0.06)",
          maxHeight: "calc(100vh - 40px)",
          overflowY: "auto",
        }}>

          {/* Hero image */}
          <div style={{ position: "relative", width: "100%", height: "235px", overflow: "hidden", background: "#0a0b12" }}>
            <Image
              src="/hollowscan_image.png"
              alt="HollowScan — Never miss a resale flip"
              fill
              style={{ objectFit: "cover", objectPosition: "center 15%" }}
              sizes="(max-width: 400px) 100vw, 360px"
              priority
            />
            {/* Subtle bottom gradient fade into card body */}
            <div style={{
              position: "absolute", inset: 0,
              background: "linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(6,8,12,0) 45%, rgba(6,8,12,0.95) 100%)",
            }} />

            {/* Close X — only button on image, top-right */}
            <button
              className="hs-close-btn"
              aria-label="Dismiss HollowScan promotion"
              onClick={dismiss}
              style={{
                position: "absolute", top: "10px", right: "10px",
                background: "rgba(0,0,0,0.48)", border: "1px solid rgba(255,255,255,0.11)",
                color: "rgba(255,255,255,0.65)",
                width: "28px", height: "28px", borderRadius: "50%",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "16px", lineHeight: 1, transition: "all 0.2s",
                backdropFilter: "blur(8px)", WebkitBackdropFilter: "blur(8px)",
              }}
            >×</button>
          </div>

          {/* Content */}
          <div style={{ padding: "18px 18px 20px" }}>
            {/* Title */}
            <h3 style={{
              color: "#ffffff", fontWeight: 800, fontSize: "16px",
              lineHeight: 1.35, margin: "0 0 9px", letterSpacing: "-0.02em",
            }}>
              £5 reward waiting.{" "}
              <span style={{
                background: "linear-gradient(90deg, #00dc64 0%, #00c4ff 100%)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}>
                Never miss a resale flip again.
              </span>
            </h3>

            {/* Description */}
            <p style={{
              color: "rgba(255,255,255,0.52)", fontSize: "13px",
              lineHeight: 1.65, margin: "0 0 18px",
            }}>
              HollowScan monitors US, UK &amp; Canada retail in real time, surfacing drops, restocks and flip
              opportunities before the crowd. Download the app and claim your £5 reward instantly.
            </p>

            {/* Feature pills */}
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "18px" }}>
              {["⚡ Real-time alerts", "🌍 US · UK · Canada", "🎁 £5 on signup"].map((label) => (
                <span key={label} style={{
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "20px", padding: "4px 10px",
                  color: "rgba(255,255,255,0.58)", fontSize: "11px", fontWeight: 500,
                }}>
                  {label}
                </span>
              ))}
            </div>

            {/* CTAs */}
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                id="hollowscan-explore-btn"
                className="hs-explore-btn"
                onClick={explore}
                style={{
                  flex: 1,
                  background: "linear-gradient(135deg, #00dc64 0%, #00a854 100%)",
                  border: "none", borderRadius: "12px",
                  color: "#000", fontWeight: 800, fontSize: "14px",
                  padding: "12px 0", cursor: "pointer",
                  transition: "all 0.28s cubic-bezier(0.34,1.56,0.64,1)",
                  letterSpacing: "-0.01em",
                  boxShadow: "0 4px 20px rgba(0,220,100,0.38)",
                }}
              >
                Explore →
              </button>
              <button
                id="hollowscan-hide-btn"
                className="hs-hide-btn"
                onClick={() => setPhase("mini")}
                style={{
                  flexShrink: 0,
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.09)",
                  borderRadius: "12px", color: "rgba(255,255,255,0.55)",
                  fontWeight: 600, fontSize: "14px",
                  padding: "12px 18px", cursor: "pointer",
                  transition: "all 0.2s", whiteSpace: "nowrap",
                }}
              >
                Hide
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
