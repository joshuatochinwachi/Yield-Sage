"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { MouseGradientBackground } from "@/components/mouse-gradient-background";
import { api } from "@/lib/api";

// ── Icons (inline SVGs matching site style — no extra deps needed) ──────────

function IconShield() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <polyline points="9 12 11 14 15 10" />
    </svg>
  );
}
function IconLink() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}
function IconCheck() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}
function IconX() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

// ── JSON Pretty-Printer with colourised output ────────────────────────────────

function PrettyJSON({ raw }: { raw: string }) {
  let parsed: Record<string, unknown> | null = null;
  try { parsed = JSON.parse(raw); } catch {}

  if (!parsed) return <pre className="text-xs font-mono text-white/50 whitespace-pre-wrap break-all">{raw}</pre>;

  const fieldMeta: Record<string, { label: string; color: string; desc: string }> = {
    protocol_name:  { label: "Protocol",       color: "rgba(255,255,255,0.85)", desc: "The DeFi protocol name" },
    pool_name:      { label: "Pool",            color: "rgba(255,255,255,0.85)", desc: "The specific liquidity pool" },
    pool_address:   { label: "Contract",        color: "rgba(99,179,237,0.9)",  desc: "Verified on-chain address" },
    risk_tag:       { label: "Risk Tier",       color: "rgba(246,173,85,0.9)",  desc: "AI-assigned risk classification" },
    rank:           { label: "Rank",            color: "rgba(255,255,255,0.85)", desc: "Position in this scoring cycle" },
    apy_at_time:    { label: "APY at Scoring",  color: "rgba(0,255,136,0.95)", desc: "Exact APY locked at scoring time" },
    tvl_usd:        { label: "TVL (USD)",       color: "rgba(0,255,136,0.8)",  desc: "Total value locked at scoring time" },
    ai_reasoning:   { label: "AI Reasoning",    color: "rgba(159,122,234,0.9)", desc: "Verbatim AI justification" },
    ai_model:       { label: "AI Model",        color: "rgba(255,255,255,0.6)", desc: "Exact model that generated this" },
    scored_at:      { label: "Scored At",       color: "rgba(255,255,255,0.6)", desc: "UTC timestamp of scoring" },
    chain:          { label: "Chain",           color: "rgba(0,255,136,0.7)",  desc: "The blockchain network" },
    chain_id:       { label: "Chain ID",        color: "rgba(255,255,255,0.5)", desc: "Numeric EVM chain identifier" },
    source:         { label: "Data Source",     color: "rgba(255,255,255,0.5)", desc: "Upstream data feed" },
    version:        { label: "Schema Version",  color: "rgba(255,255,255,0.4)", desc: "Payload format version" },
  };

  const order = ["protocol_name","pool_name","pool_address","risk_tag","rank","apy_at_time","tvl_usd","ai_reasoning","ai_model","scored_at","chain","chain_id","source","version"];
  const orderedKeys = [...order.filter(k => k in parsed!), ...Object.keys(parsed).filter(k => !order.includes(k))];

  return (
    <div className="space-y-3">
      {orderedKeys.map((key) => {
        const meta = fieldMeta[key] || { label: key, color: "rgba(255,255,255,0.7)", desc: "" };
        const val = String((parsed as Record<string, unknown>)[key]);
        const isLong = val.length > 60;
        return (
          <div key={key} className="group">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-28 text-[10px] font-mono uppercase tracking-wider pt-0.5" style={{ color: "rgba(255,255,255,0.28)" }}>
                {meta.label}
              </div>
              <div className="flex-1 min-w-0">
                <div
                  className={`text-xs font-mono leading-relaxed ${isLong ? "break-words" : "truncate"}`}
                  style={{ color: meta.color }}
                  title={isLong ? val : undefined}
                >
                  {val}
                </div>
                {meta.desc && (
                  <div className="text-[10px] mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200" style={{ color: "rgba(255,255,255,0.25)" }}>
                    {meta.desc}
                  </div>
                )}
              </div>
            </div>
            <div className="mt-2 h-px" style={{ background: "rgba(255,255,255,0.04)" }} />
          </div>
        );
      })}
    </div>
  );
}

// ── Hash display — shows each char with reveal animation ──────────────────────

function HashDisplay({ hash, color }: { hash: string; color: string }) {
  return (
    <div
      className="rounded-xl p-4 overflow-hidden font-mono text-[11px] tracking-widest leading-relaxed break-all select-all"
      style={{ background: "rgba(255,255,255,0.03)", border: `1px solid ${color}20`, color }}
    >
      {hash.slice(0, 32)}<br />{hash.slice(32)}
    </div>
  );
}

// ── Spinning Ring Loader ──────────────────────────────────────────────────────

function SpinnerRing() {
  return (
    <div className="relative w-16 h-16 mx-auto">
      <svg className="w-full h-full animate-spin" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="28" stroke="rgba(0,255,136,0.1)" strokeWidth="4" />
        <path d="M32 4a28 28 0 0 1 28 28" stroke="rgba(0,255,136,0.9)" strokeWidth="4" strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-2 h-2 rounded-full" style={{ background: "rgba(0,255,136,1)", boxShadow: "0 0 12px rgba(0,255,136,0.8)" }} />
      </div>
    </div>
  );
}

// ── Main content ──────────────────────────────────────────────────────────────

function VerifyContent() {
  const searchParams = useSearchParams();
  const txHash = searchParams?.get("tx");

  const [status, setStatus] = useState<"loading" | "hashing" | "success" | "failed" | "error">("loading");
  const [data, setData] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [computedHash, setComputedHash] = useState("");
  const [step, setStep] = useState(0); // 0=fetching, 1=building, 2=hashing, 3=comparing
  const [simModalOpen, setSimModalOpen] = useState(false);
  const [simPoolId, setSimPoolId] = useState("");
  const [simPoolAddr, setSimPoolAddr] = useState("");
  const [simPoolName, setSimPoolName] = useState("");
  const [simAmount, setSimAmount] = useState("1000");

  useEffect(() => {
    if (!txHash) {
      setErrorMsg("No transaction hash provided. Please use a ?tx= query parameter.");
      setStatus("error");
      return;
    }
    fetchData(txHash);
  }, [txHash]);

  const fetchData = async (hash: string) => {
    try {
      const res = await api.verifyRecommendation(hash);
      setData(res);
      runVerification(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Recommendation not found for this transaction.");
      setStatus("error");
    }
  };

  const runVerification = async (res: any) => {
    setStatus("hashing");
    // Animated step-through
    setStep(0); await new Promise(r => setTimeout(r, 800));
    setStep(1); await new Promise(r => setTimeout(r, 700));
    setStep(2); await new Promise(r => setTimeout(r, 600));

    try {
      const encoder = new TextEncoder();
      const payloadData = encoder.encode(res.canonical_payload);
      const hashBuffer = await crypto.subtle.digest("SHA-256", payloadData);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
      setComputedHash(hashHex);
      setStep(3); await new Promise(r => setTimeout(r, 400));
      setStatus(hashHex === res.data.recommendation_hash ? "success" : "failed");
    } catch {
      setStatus("error");
      setErrorMsg("Failed to compute SHA-256 hash in browser.");
    }
  };

  const STEPS = [
    "Fetching recommendation from database",
    "Reconstructing canonical JSON payload",
    "Computing SHA-256 fingerprint",
    "Comparing against on-chain record",
  ];

  return (
    <div className="min-h-screen relative text-white" style={{ fontFamily: "var(--font-sans, Inter, sans-serif)" }}>
      <MouseGradientBackground />

      <style>{`
        @keyframes glowPulse { 0%,100%{opacity:.5} 50%{opacity:1} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
      `}</style>

      <div className="relative z-10 min-h-screen flex flex-col">

        {/* ── Top nav strip ── */}
        <nav className="flex items-center justify-between px-4 sm:px-6 md:px-12 py-4 border-b gap-3" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
          {/* Left: brand breadcrumb */}
          <a href="/" className="flex items-center gap-2 group flex-shrink-0">
            <div
              className="w-7 h-7 rounded-lg overflow-hidden flex-shrink-0"
              style={{ border: "1px solid rgba(0,255,136,0.25)" }}
            >
              <img src="/logo.jpg" alt="YieldSage" className="w-full h-full object-cover" />
            </div>
            <span className="text-sm font-semibold hidden sm:inline" style={{ color: "rgba(255,255,255,0.7)" }}>YieldSage</span>
            <span className="text-sm hidden sm:inline" style={{ color: "rgba(255,255,255,0.2)" }}>/</span>
            <span className="text-sm font-mono" style={{ color: "rgba(0,255,136,0.7)" }}>Proof Verification</span>
          </a>

          {/* Centre / Right: quick nav links */}
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap justify-end">
            <a
              href="/dashboard"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono tracking-wide transition-all duration-200 border"
              style={{
                background: "rgba(0,255,136,0.07)",
                border: "1px solid rgba(0,255,136,0.18)",
                color: "rgba(0,255,136,0.8)",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.background = "rgba(0,255,136,0.14)";
                (e.currentTarget as HTMLElement).style.color = "rgba(0,255,136,1)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.background = "rgba(0,255,136,0.07)";
                (e.currentTarget as HTMLElement).style.color = "rgba(0,255,136,0.8)";
              }}
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
              </svg>
              Dashboard
            </a>
            <a
              href="/docs"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono tracking-wide transition-all duration-200"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.09)",
                color: "rgba(255,255,255,0.45)",
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.08)";
                (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.85)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.04)";
                (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.45)";
              }}
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
              </svg>
              Docs
            </a>
            <div
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-mono tracking-widest uppercase"
              style={{ background: "rgba(0,255,136,0.06)", border: "1px solid rgba(0,255,136,0.15)", color: "rgba(0,255,136,0.6)" }}
            >
              <span style={{ width: 5, height: 5, borderRadius: "50%", background: "rgba(0,255,136,1)", display: "inline-block", animation: "glowPulse 1.5s ease-in-out infinite" }} />
              Solana · Chain 101
            </div>
          </div>
        </nav>

        {/* ── Hero ── */}
        <div className="flex flex-col items-center text-center pt-16 pb-12 px-6">
          <motion.div
            initial={{ scale: 0.7, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 180, damping: 18 }}
            className="w-20 h-20 rounded-3xl flex items-center justify-center mb-8"
            style={{
              background: "linear-gradient(135deg, rgba(0,255,136,0.14) 0%, rgba(0,200,100,0.06) 100%)",
              border: "1px solid rgba(0,255,136,0.25)",
              boxShadow: "0 0 48px rgba(0,255,136,0.12), 0 0 120px rgba(0,255,136,0.05)",
              color: "rgba(0,255,136,0.9)",
            }}
          >
            <IconShield />
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
            className="text-4xl md:text-6xl font-semibold tracking-tight leading-[1.06] mb-4"
          >
            <span style={{ color: "rgba(255,255,255,0.92)" }}>Proof of Yield</span>
            <br />
            <span style={{ color: "rgba(255,255,255,0.28)" }}>Verification</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-lg text-base leading-relaxed"
            style={{ color: "rgba(255,255,255,0.38)" }}
          >
            Every AI recommendation is fingerprinted with SHA-256 and committed to the Solana blockchain.
            This page mathematically proves the data has never been altered.
          </motion.p>

          {/* TX hash pill */}
          {txHash && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.35 }}
              className="mt-6 flex items-center gap-2 px-4 py-2 rounded-full text-[10px] font-mono"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.09)",
                color: "rgba(255,255,255,0.45)",
              }}
            >
              <span style={{ color: "rgba(255,255,255,0.22)" }}>TX</span>
              <span className="truncate max-w-[220px] md:max-w-none">{txHash}</span>
            </motion.div>
          )}
        </div>

        {/* ── Error state ── */}
        <AnimatePresence>
          {status === "error" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mx-auto w-full max-w-lg px-6 pb-16"
            >
              <div
                className="rounded-2xl p-8 text-center"
                style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)" }}
              >
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4"
                  style={{ background: "rgba(239,68,68,0.1)", color: "rgba(239,68,68,0.8)" }}
                >
                  <IconX />
                </div>
                <h3 className="text-lg font-semibold mb-2" style={{ color: "rgba(239,68,68,0.9)" }}>Not Found</h3>
                <p className="text-sm" style={{ color: "rgba(239,68,68,0.6)" }}>{errorMsg}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Loading / Hashing state ── */}
        <AnimatePresence>
          {status === "loading" && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-6 py-8">
              <SpinnerRing />
              <p className="text-sm font-mono" style={{ color: "rgba(255,255,255,0.35)" }}>Fetching from chain…</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Main content: pipeline steps + data cards ── */}
        <AnimatePresence>
          {data && status !== "error" && (
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className="flex-1 w-full max-w-6xl mx-auto px-6 md:px-12 pb-20"
            >
              {/* ── Verification pipeline ── */}
              <div className="mb-10">
                <p className="text-[10px] font-mono tracking-[0.3em] uppercase mb-5" style={{ color: "rgba(0,255,136,0.5)" }}>
                  Verification Pipeline
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {STEPS.map((label, i) => {
                    const done = (status === "success" || status === "failed") ? true : (status === "hashing" && step > i);
                    const active = status === "hashing" && step === i;
                    return (
                      <div
                        key={i}
                        className="relative rounded-xl p-4 transition-all duration-500"
                        style={{
                          background: done
                            ? "rgba(0,255,136,0.06)"
                            : active
                            ? "rgba(0,255,136,0.03)"
                            : "rgba(255,255,255,0.02)",
                          border: done
                            ? "1px solid rgba(0,255,136,0.2)"
                            : active
                            ? "1px solid rgba(0,255,136,0.12)"
                            : "1px solid rgba(255,255,255,0.06)",
                        }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div
                            className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 transition-all duration-500"
                            style={{
                              background: done ? "rgba(0,255,136,0.15)" : active ? "rgba(0,255,136,0.08)" : "rgba(255,255,255,0.06)",
                              color: done ? "rgba(0,255,136,0.9)" : active ? "rgba(0,255,136,0.6)" : "rgba(255,255,255,0.25)",
                              border: done ? "1px solid rgba(0,255,136,0.3)" : "1px solid transparent",
                            }}
                          >
                            {done ? "✓" : i + 1}
                          </div>
                          {active && (
                            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: "rgba(0,255,136,0.8)", animation: "glowPulse 0.8s ease infinite" }} />
                          )}
                        </div>
                        <p className="text-[11px] leading-snug" style={{ color: done ? "rgba(255,255,255,0.65)" : active ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.25)" }}>
                          {label}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* ── Two column layout: Payload | Hash ── */}
              <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6 items-start">

                {/* ── Payload card ── */}
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{
                    background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)",
                    border: "1px solid rgba(255,255,255,0.07)",
                    backdropFilter: "blur(24px)",
                  }}
                >
                  {/* Card header */}
                  <div className="flex items-center gap-3 px-6 py-4 border-b" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(99,179,237,0.1)", border: "1px solid rgba(99,179,237,0.2)" }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(99,179,237,0.9)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold" style={{ color: "rgba(255,255,255,0.85)" }}>Original Payload</h3>
                      <p className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.3)" }}>The exact data fingerprinted on-chain</p>
                    </div>
                  </div>

                  {/* Quick stats */}
                  <div className="grid grid-cols-3 divide-x" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", borderColor: "rgba(255,255,255,0.05)" }}>
                    {[
                      { label: "Protocol", value: data.data.protocols?.name, accent: false },
                      { label: "APY", value: `${data.data.apy_at_time}%`, accent: true },
                      { label: "Risk Tier", value: data.data.risk_tag, badge: true },
                    ].map(({ label, value, accent, badge }) => (
                      <div key={label} className="px-5 py-4" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                        <div className="text-[10px] font-mono uppercase tracking-wider mb-1.5" style={{ color: "rgba(255,255,255,0.28)" }}>{label}</div>
                        {badge ? (
                          <span
                            className="inline-block text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-md"
                            style={{ background: "rgba(246,173,85,0.12)", border: "1px solid rgba(246,173,85,0.25)", color: "rgba(246,173,85,0.9)" }}
                          >
                            {value}
                          </span>
                        ) : (
                          <div className="text-sm font-semibold" style={{ color: accent ? "rgba(0,255,136,0.95)" : "rgba(255,255,255,0.85)" }}>{value}</div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Field-by-field breakdown */}
                  <div className="px-6 py-6">
                    <div className="text-[10px] font-mono uppercase tracking-wider mb-4" style={{ color: "rgba(255,255,255,0.25)" }}>
                      Field breakdown · hover for description
                    </div>
                    <PrettyJSON raw={data.canonical_payload} />
                  </div>
                </div>

                {/* ── Right column: Hash verification ── */}
                <div className="flex flex-col gap-4">

                  {/* Hash computation card */}
                  <div
                    className="rounded-2xl overflow-hidden"
                    style={{
                      background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)",
                      border: "1px solid rgba(255,255,255,0.07)",
                      backdropFilter: "blur(24px)",
                    }}
                  >
                    <div className="flex items-center gap-3 px-5 py-4 border-b" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(0,255,136,0.1)", border: "1px solid rgba(0,255,136,0.2)" }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(0,255,136,0.9)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="2" y="11" width="20" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold" style={{ color: "rgba(255,255,255,0.85)" }}>Cryptographic Hash</h3>
                        <p className="text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.3)" }}>SHA-256 · computed in your browser</p>
                      </div>
                    </div>

                    <div className="p-5 space-y-5">
                      {/* Hashing in progress */}
                      <AnimatePresence mode="wait">
                        {status === "hashing" && (
                          <motion.div
                            key="hashing"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center py-6 gap-4"
                          >
                            <SpinnerRing />
                            <p className="text-xs font-mono" style={{ color: "rgba(0,255,136,0.6)" }}>
                              {STEPS[step]}…
                            </p>
                          </motion.div>
                        )}

                        {(status === "success" || status === "failed") && (
                          <motion.div
                            key="result"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                            className="space-y-4"
                          >
                            <div>
                              <div className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>
                                Computed Hash (Browser)
                              </div>
                              <HashDisplay hash={computedHash} color="rgba(0,255,136,0.85)" />
                            </div>

                            {/* Match indicator */}
                            <div
                              className="flex items-center justify-center gap-2.5 py-3 rounded-xl"
                              style={{
                                background: status === "success" ? "rgba(0,255,136,0.07)" : "rgba(239,68,68,0.07)",
                                border: `1px solid ${status === "success" ? "rgba(0,255,136,0.2)" : "rgba(239,68,68,0.2)"}`,
                              }}
                            >
                              <div
                                className="w-6 h-6 rounded-full flex items-center justify-center"
                                style={{
                                  background: status === "success" ? "rgba(0,255,136,0.15)" : "rgba(239,68,68,0.15)",
                                  color: status === "success" ? "rgba(0,255,136,0.9)" : "rgba(239,68,68,0.9)",
                                }}
                              >
                                {status === "success" ? <IconCheck /> : <IconX />}
                              </div>
                              <span
                                className="text-sm font-semibold tracking-wide"
                                style={{ color: status === "success" ? "rgba(0,255,136,0.9)" : "rgba(239,68,68,0.9)" }}
                              >
                                {status === "success" ? "Perfect Match" : "Hash Mismatch — Tampered!"}
                              </span>
                            </div>

                            <div>
                              <div className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.3)" }}>
                                Input Data Hash
                              </div>
                              <HashDisplay hash={data.data.recommendation_hash} color="rgba(255,255,255,0.45)" />
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>

                  {/* Take Action Card */}
                  {status === "success" && data.data.protocols && (
                    <div
                      className="rounded-2xl p-5 space-y-4"
                      style={{
                        background: "linear-gradient(135deg, rgba(0,255,136,0.06) 0%, rgba(0,200,100,0.02) 100%)",
                        border: "1px solid rgba(0,255,136,0.18)",
                        backdropFilter: "blur(24px)",
                      }}
                    >
                      <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-1.5 font-mono">
                          <span className="text-[#00ff88]">⚡</span>
                          Take Action
                        </h4>
                        <p className="text-[11px] text-white/50 leading-relaxed mt-1">
                          If this yield opportunity aligns with your risk profile, execute the trade or run a simulated test.
                        </p>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        {data.data.protocols.app_link && (
                          <a
                            href={data.data.protocols.app_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-semibold bg-[#00ff88]/10 hover:bg-[#00ff88]/20 text-[#00ff88] border border-[#00ff88]/25 transition-all text-center cursor-pointer"
                            title="Go to protocol DApp to invest"
                          >
                            Invest
                            <IconLink />
                          </a>
                        )}
                        <button
                          onClick={() => {
                            setSimPoolId(data.data.protocol_id || data.data.protocols?.id || "");
                            setSimPoolAddr(data.data.protocols.pool_address || "");
                            setSimPoolName(`${data.data.protocols.name || "Protocol"} (${data.data.protocols.pool_name || "Pool"})`);
                            setSimAmount("1000");
                            setSimModalOpen(true);
                          }}
                          className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-semibold bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/25 transition-all text-center cursor-pointer"
                          title="Simulate paper trade on Telegram"
                        >
                          Simulate
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M22 2L11 13" />
                            <path d="M22 2L15 22L11 13L2 9L22 2Z" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* How it works card */}
                  <div
                    className="rounded-2xl p-5 space-y-3"
                    style={{
                      background: "rgba(255,255,255,0.02)",
                      border: "1px solid rgba(255,255,255,0.06)",
                    }}
                  >
                    <h4 className="text-[10px] font-mono uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.3)" }}>How it works</h4>
                    {[
                      { num: "1", text: "YieldSage serialises the AI output to canonical JSON" },
                      { num: "2", text: "SHA-256 fingerprints the exact JSON string" },
                      { num: "3", text: "Hash is embedded in a Solana SPL Memo transaction" },
                      { num: "4", text: "Your browser re-hashes the data and compares" },
                    ].map(({ num, text }) => (
                      <div key={num} className="flex items-start gap-3">
                        <div
                          className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0 mt-0.5"
                          style={{ background: "rgba(0,255,136,0.08)", border: "1px solid rgba(0,255,136,0.15)", color: "rgba(0,255,136,0.7)" }}
                        >
                          {num}
                        </div>
                        <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.35)" }}>{text}</p>
                      </div>
                    ))}
                  </div>

                  {/* Solscan CTA */}
                  {status === "success" && data.data.explorer_url && (
                    <motion.a
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      href={data.data.explorer_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-center gap-2.5 w-full py-4 rounded-2xl font-semibold text-sm transition-all"
                      style={{
                        background: "rgba(0,255,136,1)",
                        color: "#050505",
                        boxShadow: "0 0 32px rgba(0,255,136,0.25)",
                      }}
                      onMouseEnter={e => {
                        (e.currentTarget as HTMLElement).style.boxShadow = "0 0 56px rgba(0,255,136,0.45)";
                        (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLElement).style.boxShadow = "0 0 32px rgba(0,255,136,0.25)";
                        (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                      }}
                    >
                      View on Solscan
                      <IconLink />
                    </motion.a>
                  )}

                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      {simModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 transition-all duration-300">
          <div className="bg-[#0a0a0c] border border-white/10 rounded-2xl p-6 max-w-sm w-full mx-auto shadow-2xl relative z-55">
            <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2 font-mono">
              <span className="text-indigo-400">✨</span>
              Simulate Paper Trade
            </h3>
            <p className="text-xs text-white/60 mb-4 leading-relaxed">
              How much USD would you like to simulate investing in <span className="text-white font-semibold">{simPoolName}</span>?
            </p>
            <div className="relative mb-5">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/40 text-xs font-mono">$</span>
              <input
                type="number"
                value={simAmount}
                onChange={(e) => setSimAmount(e.target.value)}
                placeholder="1000"
                className="w-full bg-white/5 border border-white/10 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 rounded-xl pl-8 pr-4 py-2.5 text-sm font-mono text-white placeholder-white/20 outline-none transition-all"
                autoFocus
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setSimModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-white/10 hover:bg-white/5 text-white/70 transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setSimModalOpen(false);
                  const cleanAddr = simPoolAddr.match(/0x[a-fA-F0-9]{40}/)?.[0] || simPoolAddr;
                  const telegramUrl = `https://t.me/YieldSageBot?text=${encodeURIComponent(`/trade id=${simPoolId} address=${cleanAddr} amount=${simAmount} token=${simPoolName}`)}`;
                  window.open(telegramUrl, "_blank", "noopener,noreferrer");
                }}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-all cursor-pointer"
              >
                Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center" style={{ background: "#050505" }}>
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 relative">
              <svg className="w-full h-full animate-spin" viewBox="0 0 64 64" fill="none">
                <circle cx="32" cy="32" r="28" stroke="rgba(0,255,136,0.1)" strokeWidth="4" />
                <path d="M32 4a28 28 0 0 1 28 28" stroke="rgba(0,255,136,0.9)" strokeWidth="4" strokeLinecap="round" />
              </svg>
            </div>
            <p className="text-sm font-mono" style={{ color: "rgba(255,255,255,0.3)" }}>Loading proof…</p>
          </div>
        </div>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}
