"use client"

import { useRef, useState, useEffect, useCallback, useMemo } from "react"
import { motion, useInView } from "framer-motion"

const API_URL = process.env.NEXT_PUBLIC_FAST_API_BACKEND_URL || "http://localhost:8000"

// ── helpers ───────────────────────────────────────────────────────────────────

function truncateHash(h: string, head = 8, tail = 6) {
  if (!h) return "—"
  return `${h.slice(0, head)}…${h.slice(-tail)}`
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60)   return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

const RISK_COLOR: Record<string, string> = {
  stable:     "rgba(0,255,136,",
  moderate:   "rgba(246,173,85,",
  aggressive: "rgba(251,113,133,",
}

// ── Protocol icon (with gradient fallback like dashboard) ─────────────────────

function ProtocolIcon({ name, imageUrl }: { name: string; imageUrl?: string }) {
  const [err, setErr] = useState(false)
  const initial = name ? name.charAt(0).toUpperCase() : "?"

  const getGradient = (s: string) => {
    let hash = 0
    for (let i = 0; i < s.length; i++) hash = s.charCodeAt(i) + ((hash << 5) - hash)
    const colors = [
      "from-[#00ff88] to-emerald-600",
      "from-cyan-500 to-blue-600",
      "from-purple-500 to-indigo-600",
      "from-pink-500 to-rose-600",
      "from-amber-500 to-orange-600",
    ]
    return colors[Math.abs(hash) % colors.length]
  }

  if (imageUrl && !err) {
    return (
      <img
        src={imageUrl}
        alt={name}
        onError={() => setErr(true)}
        className="w-8 h-8 rounded-full border border-white/10 bg-black/40 object-cover flex-shrink-0"
      />
    )
  }

  return (
    <div
      className={`w-8 h-8 rounded-full bg-gradient-to-br ${getGradient(name)} flex items-center justify-center border border-white/10 shadow-[0_0_10px_rgba(255,255,255,0.05)] text-xs font-bold text-white uppercase flex-shrink-0`}
    >
      {initial}
    </div>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

const PAGE_SIZE = 8

export function OnChainProofSection() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: "-80px" })

  const [recs, setRecs]               = useState<any[]>([])
  const [page, setPage]               = useState(1)
  const [hasMore, setHasMore]         = useState(false)
  const [lastFetched, setLastFetched] = useState<Date | null>(null)
  const [loading, setLoading]         = useState(false)
  const [search, setSearch]           = useState("")

  const fetchPage = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const res = await fetch(
        `${API_URL}/api/recommendations/history?page=${p}&page_size=${PAGE_SIZE}`
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      const list: any[] = Array.isArray(json.data) ? json.data : []
      const verified = list.filter((r: any) => !!r.on_chain_tx_hash)
      setRecs(verified)
      setHasMore(json.has_more === true)
      setLastFetched(new Date())
      setPage(p)
    } catch {
      // leave previous data intact on error
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPage(1)
    const id = setInterval(() => fetchPage(1), 5 * 60 * 1000)
    return () => clearInterval(id)
  }, [fetchPage])

  // ── Client-side search across all loaded records ──────────────────────────
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return recs
    return recs.filter((r: any) => {
      const protocol  = r.protocols?.name?.toLowerCase() || ""
      const poolName  = r.protocols?.pool_name?.toLowerCase() || ""
      const poolAddr  = (r.protocols?.pool_address || "").toLowerCase()
      const txHash    = (r.on_chain_tx_hash || "").toLowerCase()
      const asset     = (r.asset || "").toLowerCase()
      return (
        protocol.includes(q) ||
        poolName.includes(q) ||
        poolAddr.includes(q) ||
        txHash.includes(q) ||
        asset.includes(q)
      )
    })
  }, [recs, search])

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <section
      ref={ref}
      id="on-chain-proof"
      className="relative py-20 md:py-36 px-4 sm:px-6 md:px-12 overflow-hidden"
      style={{ background: "transparent" }}
    >
      <style>{`
        @keyframes glowPulse { 0%,100%{opacity:.45} 50%{opacity:.9} }
        @keyframes tableFadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        .proof-search-input::placeholder { color: rgba(255,255,255,0.22); }
        .proof-search-input:focus { outline: none; border-color: rgba(0,255,136,0.35); box-shadow: 0 0 0 2px rgba(0,255,136,0.08); }
      `}</style>

      {/* Ambient */}
      <div className="absolute inset-0 pointer-events-none" style={{ background: "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0,255,136,0.03) 0%, transparent 65%)" }} />
      <div className="absolute top-0 inset-x-0 h-px" style={{ background: "linear-gradient(to right,transparent 0%,rgba(255,255,255,0.04) 25%,rgba(0,255,136,0.12) 50%,rgba(255,255,255,0.04) 75%,transparent 100%)" }} />

      <div className="max-w-6xl mx-auto relative z-10">

        {/* ── Section header ── */}
        <div className="flex flex-col items-center text-center mb-12 md:mb-16">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="text-[10px] tracking-[0.4em] uppercase font-mono mb-5"
            style={{ color: "rgba(0,255,136,0.6)" }}
          >
            On-Chain Verifiability
          </motion.p>

          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="text-2xl sm:text-3xl md:text-5xl font-semibold tracking-tight leading-tight mb-5"
            style={{ color: "rgba(255,255,255,0.9)" }}
          >
            Cryptographic Proof of Intelligence.
            <br className="hidden md:block" />
            <span style={{ color: "rgba(255,255,255,0.45)" }}>Every decision, permanently verifiable.</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="max-w-lg text-sm leading-relaxed px-4"
            style={{ color: "rgba(255,255,255,0.35)" }}
          >
            Before writing to the database, YieldSage fingerprints every recommendation
            with SHA-256 and commits the hash to Mantle. Anyone — anytime — can verify the
            AI's exact output was never altered.
          </motion.p>
        </div>

        {/* ── How-it-works 3-step ── */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10 md:mb-12"
        >
          {[
            {
              n: "01",
              icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>,
              title: "AI Scores",
              desc: "The AI analyses all Mantle pools and produces a ranked recommendation with full reasoning.",
              color: "rgba(99,179,237,",
            },
            {
              n: "02",
              icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="11" width="20" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>,
              title: "SHA-256 Fingerprint",
              desc: "The exact JSON payload is hashed. Any future alteration — even one byte — produces a completely different hash.",
              color: "rgba(0,255,136,",
            },
            {
              n: "03",
              icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>,
              title: "Committed On-Chain",
              desc: "The hash is embedded in a Mantle transaction. It becomes immutable, publicly auditable, forever.",
              color: "rgba(246,173,85,",
            },
          ].map(({ n, icon, title, desc, color }, i) => (
            <motion.div
              key={n}
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.65, delay: 0.3 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}
              className="group relative rounded-2xl p-6 transition-all duration-500"
              style={{
                background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)",
                border: "1px solid rgba(255,255,255,0.07)",
                backdropFilter: "blur(24px)",
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLDivElement
                el.style.borderColor = `${color}0.18)`
                el.style.background = `linear-gradient(135deg, ${color}0.06) 0%, rgba(255,255,255,0.01) 100%)`
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLDivElement
                el.style.borderColor = "rgba(255,255,255,0.07)"
                el.style.background = "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)"
              }}
            >
              <div className="absolute -top-10 -right-10 w-28 h-28 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" style={{ background: `radial-gradient(circle, ${color}0.1) 0%, transparent 70%)` }} />
              <div className="flex items-start gap-4 mb-4">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${color}0.1)`, border: `1px solid ${color}0.2)`, color: `${color}0.85)` }}>
                  {icon}
                </div>
                <span className="text-3xl font-bold mt-0.5 leading-none" style={{ color: `${color}0.12)` }}>{n}</span>
              </div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: "rgba(255,255,255,0.82)" }}>{title}</h3>
              <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.35)" }}>{desc}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* ── Historical proofs table ── */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="rounded-2xl overflow-hidden"
          style={{
            background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          {/* Table header */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 px-4 sm:px-6 py-4 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
            {/* Left: status + label */}
            <div className="flex items-center gap-2.5 flex-shrink-0">
              {loading ? (
                <div className="w-1.5 h-1.5 rounded-full" style={{ background: "rgba(246,173,85,0.8)", animation: "glowPulse 0.8s ease infinite" }} />
              ) : (
                <div className="w-1.5 h-1.5 rounded-full" style={{ background: "rgba(0,255,136,1)", boxShadow: "0 0 8px rgba(0,255,136,0.9)", animation: "glowPulse 1.5s ease infinite" }} />
              )}
              <span className="text-[10px] font-mono tracking-[0.3em] uppercase whitespace-nowrap" style={{ color: "rgba(255,255,255,0.4)" }}>
                Historical On-Chain Proofs
              </span>
            </div>

            {/* Centre: search */}
            <div className="relative flex-1 min-w-0">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search pool, protocol, address, TX hash…"
                className="proof-search-input w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-1.5 text-[11px] font-mono text-white transition-all duration-200"
                style={{ color: "rgba(255,255,255,0.8)" }}
              />
              {search && (
                <button
                  onClick={() => setSearch("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/70 transition-colors"
                  aria-label="Clear search"
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              )}
            </div>

            {/* Right: updated + refresh */}
            <div className="flex items-center gap-3 flex-shrink-0">
              {lastFetched && (
                <span className="text-[9px] font-mono hidden sm:block" style={{ color: "rgba(255,255,255,0.2)" }}>
                  Updated {timeAgo(lastFetched.toISOString())}
                </span>
              )}
              <button
                onClick={() => fetchPage(1)}
                disabled={loading}
                className="text-[10px] font-mono tracking-wider uppercase transition-colors whitespace-nowrap"
                style={{ color: "rgba(0,255,136,0.5)", cursor: loading ? "wait" : "pointer" }}
                onMouseEnter={e => !loading && ((e.currentTarget as HTMLElement).style.color = "rgba(0,255,136,0.9)")}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = "rgba(0,255,136,0.5)")}
              >
                {loading ? "Refreshing…" : "↻ Refresh"}
              </button>
            </div>
          </div>

          {/* Column headers – desktop */}
          <div className="hidden md:grid md:grid-cols-[2fr_80px_90px_140px_130px] gap-4 px-6 py-2.5 border-b" style={{ borderColor: "rgba(255,255,255,0.04)" }}>
            {["Protocol · Pool", "APY", "Risk", "TX Hash", "Actions"].map(h => (
              <span key={h} className="text-[9px] font-mono uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.22)" }}>{h}</span>
            ))}
          </div>

          {/* Empty / loading */}
          {filtered.length === 0 && !loading && (
            <div className="px-6 py-12 text-center">
              <p className="text-sm font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>
                {search
                  ? `No proofs matching "${search}".`
                  : "No on-chain proofs yet. First scoring cycle commits data here."}
              </p>
            </div>
          )}

          {loading && recs.length === 0 && (
            <div className="px-6 py-12 flex items-center justify-center gap-3">
              <div className="w-4 h-4 relative">
                <svg className="w-full h-full animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="rgba(0,255,136,0.15)" strokeWidth="3" />
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="rgba(0,255,136,0.8)" strokeWidth="3" strokeLinecap="round" />
                </svg>
              </div>
              <span className="text-xs font-mono" style={{ color: "rgba(255,255,255,0.3)" }}>Fetching proofs from chain…</span>
            </div>
          )}

          {/* Rows */}
          {filtered.map((rec: any, i: number) => {
            const txHash   = rec.on_chain_tx_hash
            const color    = RISK_COLOR[rec.risk_tag?.toLowerCase()] || "rgba(255,255,255,0.6,"
            const scored   = rec.on_chain_logged_at || rec.created_at
            const poolAddr = rec.protocols?.pool_address || ""
            const explorerLink = poolAddr
              ? (poolAddr.startsWith("http") ? poolAddr : `https://mantlescan.xyz/address/${poolAddr}`)
              : null
            const protocolName = rec.protocols?.name || "—"
            const poolName     = rec.protocols?.pool_name || "—"
            const imageUrl     = rec.protocols?.image_url

            return (
              <div
                key={`${txHash}-${i}`}
                className="group transition-colors"
                style={{
                  borderBottom: i < filtered.length - 1 ? "1px solid rgba(255,255,255,0.035)" : "none",
                  animation: `tableFadeIn 0.4s ease ${i * 0.05}s both`,
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.02)" }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = "transparent" }}
              >
                {/* ── Desktop row layout ── */}
                <div className="hidden md:grid md:grid-cols-[2fr_80px_90px_140px_130px] gap-4 px-6 py-4 items-center">
                  {/* Protocol · Pool with icon + link */}
                  <div className="flex items-center gap-3 min-w-0">
                    <ProtocolIcon name={protocolName} imageUrl={imageUrl} />
                    <div className="min-w-0">
                      <div className="text-sm font-semibold truncate" style={{ color: "rgba(255,255,255,0.82)" }}>
                        {explorerLink ? (
                          <a
                            href={explorerLink}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline flex items-center gap-1 group-hover:text-[#00ff88] transition-colors"
                          >
                            {protocolName}
                            <svg className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                          </a>
                        ) : (
                          <span>{protocolName}</span>
                        )}
                      </div>
                      <div className="text-[10px] font-mono mt-0.5 truncate" style={{ color: "rgba(255,255,255,0.3)" }}>
                        {poolName}
                        {scored && <span className="ml-2 text-[9px]" style={{ color: "rgba(255,255,255,0.18)" }}>· {timeAgo(scored)}</span>}
                      </div>
                    </div>
                  </div>

                  {/* APY */}
                  <div className="text-sm font-semibold font-mono" style={{ color: "rgba(0,255,136,0.9)" }}>
                    {Number(rec.apy_at_time).toFixed(2)}%
                  </div>

                  {/* Risk badge */}
                  <div>
                    <span
                      className="inline-block text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded-md"
                      style={{
                        background: `${color}0.08)`,
                        border: `1px solid ${color}0.22)`,
                        color: `${color}0.88)`,
                      }}
                    >
                      {rec.risk_tag}
                    </span>
                  </div>

                  {/* TX hash */}
                  <div
                    className="text-[10px] font-mono truncate"
                    title={txHash}
                    style={{ color: "rgba(255,255,255,0.28)" }}
                  >
                    {truncateHash(txHash, 10, 8)}
                  </div>

                  {/* Action links */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <a
                      href={`/verify?tx=${txHash}`}
                      className="inline-flex items-center gap-1 text-[10px] font-mono transition-colors"
                      style={{ color: "rgba(0,255,136,0.55)" }}
                      onMouseEnter={e => (e.currentTarget.style.color = "rgba(0,255,136,0.95)")}
                      onMouseLeave={e => (e.currentTarget.style.color = "rgba(0,255,136,0.55)")}
                    >
                      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
                      Verify
                    </a>
                    <span style={{ color: "rgba(255,255,255,0.1)" }}>·</span>
                    <a
                      href={`https://mantlescan.xyz/tx/${txHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] font-mono transition-colors"
                      style={{ color: "rgba(255,255,255,0.25)" }}
                      onMouseEnter={e => (e.currentTarget.style.color = "rgba(255,255,255,0.65)")}
                      onMouseLeave={e => (e.currentTarget.style.color = "rgba(255,255,255,0.25)")}
                    >
                      ⛓ Chain
                    </a>
                  </div>
                </div>

                {/* ── Mobile card layout ── */}
                <div className="md:hidden px-4 py-4">
                  <div className="flex items-start gap-3 mb-3">
                    <ProtocolIcon name={protocolName} imageUrl={imageUrl} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div>
                          {explorerLink ? (
                            <a
                              href={explorerLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm font-semibold text-white hover:text-[#00ff88] transition-colors flex items-center gap-1"
                            >
                              {protocolName}
                              <svg className="w-3 h-3 opacity-60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                            </a>
                          ) : (
                            <span className="text-sm font-semibold" style={{ color: "rgba(255,255,255,0.82)" }}>{protocolName}</span>
                          )}
                          <div className="text-[10px] font-mono mt-0.5" style={{ color: "rgba(255,255,255,0.3)" }}>{poolName}</div>
                        </div>
                        <div className="text-base font-bold font-mono" style={{ color: "rgba(0,255,136,0.9)" }}>
                          {Number(rec.apy_at_time).toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 mb-3">
                    <span
                      className="inline-block text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-md"
                      style={{
                        background: `${color}0.08)`,
                        border: `1px solid ${color}0.22)`,
                        color: `${color}0.88)`,
                      }}
                    >
                      {rec.risk_tag}
                    </span>
                    {scored && (
                      <span className="text-[9px] font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>
                        {timeAgo(scored)}
                      </span>
                    )}
                  </div>

                  <div className="text-[10px] font-mono mb-3 truncate" title={txHash} style={{ color: "rgba(255,255,255,0.28)" }}>
                    TX: {truncateHash(txHash, 10, 8)}
                  </div>

                  <div className="flex items-center gap-3">
                    <a
                      href={`/verify?tx=${txHash}`}
                      className="inline-flex items-center gap-1 text-[10px] font-mono px-2.5 py-1 rounded-lg transition-colors"
                      style={{ background: "rgba(0,255,136,0.08)", border: "1px solid rgba(0,255,136,0.18)", color: "rgba(0,255,136,0.8)" }}
                    >
                      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
                      Verify Proof
                    </a>
                    <a
                      href={`https://mantlescan.xyz/tx/${txHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] font-mono px-2.5 py-1 rounded-lg transition-colors"
                      style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.4)" }}
                    >
                      ⛓ Mantlescan
                    </a>
                  </div>
                </div>
              </div>
            )
          })}

          {/* ── Pagination footer ── */}
          {(recs.length > 0 || page > 1) && (
            <div
              className="px-4 sm:px-6 py-4 border-t flex flex-wrap items-center justify-between gap-3"
              style={{ borderColor: "rgba(255,255,255,0.05)" }}
            >
              {/* Left: count + search result summary */}
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-[9px] font-mono" style={{ color: "rgba(255,255,255,0.2)" }}>
                  Page {page} · {filtered.length} record{filtered.length !== 1 ? "s" : ""}
                  {search && ` matching "${search}"`}
                </span>
                {lastFetched && (
                  <span className="text-[9px] font-mono hidden sm:block" style={{ color: "rgba(255,255,255,0.13)" }}>
                    · Updated {lastFetched.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </span>
                )}
              </div>

              {/* Right: prev / page pill / next */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => !loading && page > 1 && fetchPage(page - 1)}
                  disabled={loading || page <= 1}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-mono transition-all"
                  style={{
                    background: page > 1 ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.02)",
                    border: "1px solid rgba(255,255,255,0.07)",
                    color: page > 1 ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.18)",
                    cursor: page > 1 && !loading ? "pointer" : "default",
                  }}
                  onMouseEnter={e => page > 1 && !loading && ((e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.9)")}
                  onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = page > 1 ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.18)")}
                >
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
                  Prev
                </button>

                <div
                  className="flex items-center justify-center min-w-[32px] h-7 px-2.5 rounded-lg text-[10px] font-mono font-semibold"
                  style={{
                    background: "rgba(0,255,136,0.1)",
                    border: "1px solid rgba(0,255,136,0.2)",
                    color: "rgba(0,255,136,0.9)",
                  }}
                >
                  {page}
                </div>

                <button
                  onClick={() => !loading && hasMore && fetchPage(page + 1)}
                  disabled={loading || !hasMore}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-mono transition-all"
                  style={{
                    background: hasMore ? "rgba(0,255,136,0.08)" : "rgba(255,255,255,0.02)",
                    border: hasMore ? "1px solid rgba(0,255,136,0.18)" : "1px solid rgba(255,255,255,0.07)",
                    color: hasMore ? "rgba(0,255,136,0.75)" : "rgba(255,255,255,0.18)",
                    cursor: hasMore && !loading ? "pointer" : "default",
                  }}
                  onMouseEnter={e => hasMore && !loading && ((e.currentTarget as HTMLElement).style.color = "rgba(0,255,136,1)")}
                  onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = hasMore ? "rgba(0,255,136,0.75)" : "rgba(255,255,255,0.18)")}
                >
                  Next
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </section>
  )
}
