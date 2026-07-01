"use client";

import { useEffect, useRef, useState } from "react";
import { MouseGradientBackground } from "@/components/mouse-gradient-background";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Terminal,
  Bot,
  Cpu,
  Database,
  Layers,
  ShieldCheck,
  ArrowLeft,
  HelpCircle,
  TrendingUp,
  BarChart2,
  RefreshCw,
  ChevronDown,
  ExternalLink,
  Shield,
  Cookie,
  Video,
} from "lucide-react";

// ── Sections list ─────────────────────────────────────────────────────────────
const sections = [
  { id: "intro",        label: "What is YieldSage",  icon: BookOpen    },
  { id: "how-it-works", label: "How It Works",        icon: Layers      },
  { id: "dashboard",   label: "Dashboard Guide",     icon: BarChart2   },
  { id: "metrics",     label: "Every Metric Explained", icon: TrendingUp  },
  { id: "ai-intel",    label: "Yield Intelligence",  icon: Cpu         },
  { id: "onchain",     label: "On-Chain Proof",       icon: ShieldCheck },
  { id: "telegram",    label: "Telegram Bot",         icon: Bot         },
  { id: "pipeline",    label: "Data Pipeline",        icon: Database    },
  { id: "api-ref",     label: "API Reference",        icon: Terminal    },
  { id: "faq",         label: "FAQ",                  icon: HelpCircle  },
];

// ── Callout box ───────────────────────────────────────────────────────────────
function Callout({
  type = "info",
  title,
  children,
}: {
  type?: "info" | "tip" | "warning" | "important";
  title?: string;
  children: React.ReactNode;
}) {
  const styles: Record<string, { bg: string; border: string; icon: string; titleColor: string }> = {
    info:      { bg: "rgba(99,179,237,0.06)",  border: "rgba(99,179,237,0.2)",  icon: "ℹ️",  titleColor: "rgba(99,179,237,0.9)"  },
    tip:       { bg: "rgba(0,255,136,0.05)",   border: "rgba(0,255,136,0.18)", icon: "💡",  titleColor: "rgba(0,255,136,0.9)"   },
    warning:   { bg: "rgba(246,173,85,0.06)",  border: "rgba(246,173,85,0.2)", icon: "⚠️",  titleColor: "rgba(246,173,85,0.9)"  },
    important: { bg: "rgba(167,139,250,0.06)", border: "rgba(167,139,250,0.2)", icon: "🔐", titleColor: "rgba(167,139,250,0.9)" },
  };
  const s = styles[type];
  return (
    <div
      className="rounded-xl p-4 my-4"
      style={{ background: s.bg, border: `1px solid ${s.border}` }}
    >
      {title && (
        <div className="text-xs font-bold uppercase tracking-wider mb-1.5 font-mono flex items-center gap-1.5" style={{ color: s.titleColor }}>
          <span>{s.icon}</span> {title}
        </div>
      )}
      <div className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.6)" }}>
        {children}
      </div>
    </div>
  );
}

// ── Metric card ───────────────────────────────────────────────────────────────
function MetricCard({
  label,
  abbr,
  color,
  example,
  description,
  detail,
}: {
  label: string;
  abbr?: string;
  color: string;
  example: string;
  description: string;
  detail: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="rounded-xl overflow-hidden border transition-all duration-300 cursor-pointer"
      style={{ background: "rgba(255,255,255,0.02)", borderColor: open ? color.replace(")", ",0.35)") : "rgba(255,255,255,0.06)" }}
      onClick={() => setOpen(!open)}
    >
      <div className="flex items-center justify-between px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex flex-col min-w-0">
            <div className="text-sm font-semibold text-white flex items-center gap-2">
              {label}
              {abbr && (
                <span
                  className="text-[9px] font-mono uppercase tracking-widest px-2 py-0.5 rounded"
                  style={{ background: `${color.replace(")", ",0.12)")}`, color: color, border: `1px solid ${color.replace(")", ",0.25)")}` }}
                >
                  {abbr}
                </span>
              )}
            </div>
            <div className="text-[10px] font-mono mt-0.5" style={{ color: "rgba(255,255,255,0.35)" }}>
              Example: <span style={{ color }}>{example}</span>
            </div>
          </div>
        </div>
        <ChevronDown
          className="w-4 h-4 flex-shrink-0 transition-transform duration-300"
          style={{ color: "rgba(255,255,255,0.3)", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        />
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-3 border-t" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
              <p className="text-sm leading-relaxed pt-4" style={{ color: "rgba(255,255,255,0.65)" }}>
                {description}
              </p>
              <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.38)" }}>
                {detail}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Command pill ──────────────────────────────────────────────────────────────
function CommandPill({ cmd, desc }: { cmd: string; desc: string }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
      <code
        className="text-xs font-mono px-3 py-1 rounded-lg flex-shrink-0 w-fit"
        style={{ background: "rgba(0,255,136,0.08)", border: "1px solid rgba(0,255,136,0.2)", color: "rgba(0,255,136,0.9)" }}
      >
        {cmd}
      </code>
      <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.5)" }}>{desc}</p>
    </div>
  );
}

// ── Step item ─────────────────────────────────────────────────────────────────
function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-5">
      <div className="flex flex-col items-center gap-1 flex-shrink-0">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold font-mono flex-shrink-0"
          style={{ background: "rgba(0,255,136,0.1)", border: "1px solid rgba(0,255,136,0.25)", color: "rgba(0,255,136,0.9)" }}
        >
          {n}
        </div>
        <div className="w-px flex-1" style={{ background: "rgba(255,255,255,0.06)", minHeight: 24 }} />
      </div>
      <div className="pb-8 min-w-0">
        <h4 className="text-sm font-semibold text-white mb-2">{title}</h4>
        <div className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.5)" }}>{children}</div>
      </div>
    </div>
  );
}

// ── Section header ────────────────────────────────────────────────────────────
function SectionHeader({ num, tag, title, sub }: { num: string; tag: string; title: string; sub?: string }) {
  return (
    <div className="space-y-2 mb-8">
      <span className="text-[10px] font-mono uppercase tracking-[0.3em]" style={{ color: "rgba(0,255,136,0.6)" }}>
        {num} / {tag}
      </span>
      <h2 className="text-2xl sm:text-3xl md:text-4xl font-light tracking-tight">{title}</h2>
      {sub && <p className="text-sm leading-relaxed max-w-2xl" style={{ color: "rgba(255,255,255,0.45)" }}>{sub}</p>}
    </div>
  );
}

// ── Endpoint block ────────────────────────────────────────────────────────────
function Endpoint({
  method, path, desc, params, example,
}: {
  method: "GET" | "POST";
  path: string;
  desc: string;
  params?: { name: string; type: string; required?: boolean; description: string }[];
  example?: string;
}) {
  const [open, setOpen] = useState(false);
  const methodColor = method === "GET" ? "rgba(0,255,136,0.9)" : "rgba(99,179,237,0.9)";
  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.07)" }}
    >
      <div
        className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div className="flex flex-col gap-1.5 min-w-0">
          <div className="flex items-center gap-3">
            <span
              className="text-[10px] font-bold font-mono px-2 py-0.5 rounded flex-shrink-0"
              style={{ background: `${methodColor.replace(")", ",0.1)")}`, color: methodColor, border: `1px solid ${methodColor.replace(")", ",0.25)")}` }}
            >
              {method}
            </span>
            <code className="text-xs font-mono whitespace-nowrap" style={{ color: "rgba(255,255,255,0.8)" }}>{path}</code>
          </div>
          <span className="text-[10px] font-mono leading-relaxed" style={{ color: "rgba(255,255,255,0.35)" }}>
            {desc}
          </span>
        </div>
        <ChevronDown className={`w-4 h-4 flex-shrink-0 ml-4 transition-transform duration-200 ${open ? "rotate-180" : ""}`} style={{ color: "rgba(255,255,255,0.3)" }} />
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t"
            style={{ borderColor: "rgba(255,255,255,0.05)" }}
          >
            <div className="p-5 space-y-4">
              <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.5)" }}>{desc}</p>
              {params && params.length > 0 && (
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.25)" }}>Parameters</div>
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr>
                        {["Param", "Type", "Req?", "Description"].map(h => (
                          <th key={h} className="text-[10px] font-mono py-1.5 pr-4" style={{ color: "rgba(255,255,255,0.3)" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {params.map(p => (
                        <tr key={p.name} className="border-t" style={{ borderColor: "rgba(255,255,255,0.04)" }}>
                          <td className="py-2 pr-4"><code className="text-[10px] font-mono text-cyan-400">{p.name}</code></td>
                          <td className="py-2 pr-4 text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.4)" }}>{p.type}</td>
                          <td className="py-2 pr-4 text-[10px] font-mono" style={{ color: p.required ? "rgba(246,173,85,0.8)" : "rgba(255,255,255,0.25)" }}>{p.required ? "Yes" : "No"}</td>
                          <td className="py-2 text-[10px]" style={{ color: "rgba(255,255,255,0.5)" }}>{p.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {example && (
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-wider mb-2" style={{ color: "rgba(255,255,255,0.25)" }}>Example Response</div>
                  <pre className="text-[10px] font-mono leading-relaxed overflow-x-auto p-4 rounded-lg" style={{ background: "rgba(0,0,0,0.4)", color: "rgba(0,255,136,0.8)" }}>{example}</pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── FAQ item ──────────────────────────────────────────────────────────────────
function FAQ({ q, children }: { q: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="border rounded-xl overflow-hidden transition-all duration-200"
      style={{ borderColor: open ? "rgba(0,255,136,0.2)" : "rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.01)" }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 text-left"
      >
        <span className="text-sm font-medium" style={{ color: open ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.7)" }}>{q}</span>
        <ChevronDown
          className="w-4 h-4 flex-shrink-0 ml-4 transition-transform duration-200"
          style={{ color: "rgba(255,255,255,0.3)", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t text-xs leading-relaxed" style={{ borderColor: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.5)", paddingTop: 14 }}>
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function DocsPage() {
  const [activeSection, setActiveSection] = useState("intro");
  const [scrollProgress, setScrollProgress] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      const offsetPosition = element.getBoundingClientRect().top + window.pageYOffset - 120;
      window.scrollTo({ top: offsetPosition, behavior: "smooth" });
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      setScrollProgress(docHeight > 0 ? Math.min(scrollTop / docHeight, 1) : 0);

      const sectionEls = sections.map(s => document.getElementById(s.id)).filter(Boolean);
      for (const el of sectionEls) {
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        if (rect.top <= window.innerHeight * 0.4 && rect.bottom >= window.innerHeight * 0.2) {
          setActiveSection(el.id);
          break;
        }
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div ref={containerRef} className="min-h-screen relative overflow-hidden bg-[#050505] text-white">
      <MouseGradientBackground />

      {/* Scroll progress bar */}
      <div className="fixed top-0 left-0 right-0 z-50 h-[2px] bg-white/5">
        <div
          className="h-full bg-gradient-to-r from-[#00ff88] to-cyan-400 transition-all duration-150"
          style={{ width: `${scrollProgress * 100}%` }}
        />
      </div>

      {/* ── Sticky header ── */}
      <header className="sticky top-0 z-40 w-full border-b border-white/5 bg-black/60 backdrop-blur-xl">
        <div className="flex flex-col w-full max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-12 py-3 gap-3">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <img src="/logo.jpg" alt="YieldSage" className="w-7 h-7 rounded-lg border border-white/10 object-cover group-hover:border-[#00ff88]/50 transition-all" />
              <span className="font-sans font-light tracking-wider text-xs text-white/90 group-hover:text-white transition-colors">
                YIELD<span className="text-[#00ff88] font-medium font-mono">SAGE</span>
              </span>
              <span className="text-[9px] font-mono text-cyan-400 border border-cyan-500/30 px-1.5 py-0.5 rounded ml-1 bg-cyan-950/20">
                DOCS
              </span>
            </Link>
            <div className="flex items-center gap-3">
              <Link href="/dashboard" className="text-xs font-mono px-3 py-1.5 rounded-lg text-[#00ff88] border border-[#00ff88]/20 bg-[#00ff88]/07 hover:bg-[#00ff88]/14 transition-all hidden sm:flex items-center gap-1.5">
                <BarChart2 className="w-3 h-3" />
                Dashboard
              </Link>
              <Link href="/" className="text-xs font-mono text-white/40 hover:text-white flex items-center gap-1 transition-colors">
                <ArrowLeft className="w-3.5 h-3.5" /> Home
              </Link>
            </div>
          </div>

          {/* Section nav pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1 mask-fade-edges scroll-smooth">
            {sections.map(section => {
              const Icon = section.icon;
              const isActive = activeSection === section.id;
              return (
                <button
                  key={section.id}
                  onClick={() => scrollToSection(section.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-mono tracking-wide uppercase transition-all duration-300 whitespace-nowrap outline-none border ${
                    isActive
                      ? "text-[#00ff88] bg-[#00ff88]/10 border-[#00ff88]/30"
                      : "text-white/40 hover:text-white/70 bg-white/5 hover:bg-white/[0.08] border-transparent"
                  }`}
                >
                  <Icon className="w-3 h-3" />
                  {section.label}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* ── Main layout ── */}
      <div className="relative z-10 w-full max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-12 py-12 grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-12 items-start">

        {/* Sidebar */}
        <aside className="hidden lg:block sticky top-32">
          <p className="text-[10px] font-mono tracking-widest uppercase text-white/30 font-semibold px-2 mb-3">
            Table of Contents
          </p>
          <nav className="flex flex-col gap-1">
            {sections.map(section => {
              const isActive = activeSection === section.id;
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => scrollToSection(section.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-all duration-200 border-l-2 flex items-center gap-2 ${
                    isActive
                      ? "text-[#00ff88] border-[#00ff88] bg-[#00ff88]/5 font-semibold"
                      : "text-white/40 hover:text-white/80 border-transparent hover:border-white/10"
                  }`}
                >
                  <Icon className="w-3 h-3 flex-shrink-0" />
                  {section.label}
                </button>
              );
            })}
          </nav>

          <div className="mt-8 p-4 rounded-xl border space-y-3" style={{ background: "rgba(0,255,136,0.04)", borderColor: "rgba(0,255,136,0.12)" }}>
            <p className="text-[10px] font-mono uppercase tracking-widest" style={{ color: "rgba(0,255,136,0.5)" }}>Quick Links</p>
            <a href="https://t.me/YieldSageBot" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-[#00ff88] transition-colors">
              <Bot className="w-3.5 h-3.5" /> Open Telegram Bot
            </a>
            <a href="https://www.youtube.com/watch?v=aUnmj3e3mjA" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-[#00ff88] transition-colors">
              <Video className="w-3.5 h-3.5" /> YouTube Video Demo
            </a>
            <a href="/dashboard" className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-[#00ff88] transition-colors">
              <BarChart2 className="w-3.5 h-3.5" /> Live Dashboard
            </a>
            <a href="/#on-chain-proof" className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-[#00ff88] transition-colors">
              <ShieldCheck className="w-3.5 h-3.5" /> On-Chain Proofs
            </a>
            <a href="/privacy" className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-[#00ff88] transition-colors">
              <Shield className="w-3.5 h-3.5" /> Privacy Policy
            </a>
            <a href="/cookies" className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-[#00ff88] transition-colors">
              <Cookie className="w-3.5 h-3.5" /> Cookie Policy
            </a>
          </div>
        </aside>

        {/* ── All content ── */}
        <div className="space-y-28 min-w-0">

          {/* ══════════════ 1. INTRO ══════════════ */}
          <section id="intro" className="scroll-mt-32">
            <SectionHeader
              num="01"
              tag="Introduction"
              title="What is YieldSage?"
              sub="A plain-English guide to the most intelligent yield platform on Mantle Network."
            />

            <div className="space-y-5 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.6)" }}>
              <p>
                <strong className="text-white">YieldSage</strong> is your personal AI-powered yield advisor for the{" "}
                <strong className="text-white">Mantle Network</strong> — a fast, low-cost blockchain built for DeFi. Think of it as having a smart financial analyst working around the clock, scanning every liquidity pool and yield farm on Mantle, ranking them by how good they are right now, and delivering that intelligence directly to you — in plain English — through a web dashboard and a Telegram bot.
              </p>
              <p>
                The problem YieldSage solves is real: DeFi opportunities on Mantle change every hour. Yields spike and drop. Protocols launch new pools. Better opportunities appear while you're asleep. Unless you manually check five different protocols every single day, you'll miss things. YieldSage does all of that monitoring for you automatically.
              </p>
              <p>
                But it goes further than just showing you numbers. YieldSage uses <strong className="text-white">artificial intelligence</strong> to actually reason about each opportunity — considering the risk, the liquidity depth, the reward structure, and whether the yield is genuinely sustainable — and then tells you what it thinks in plain, honest language that anyone can understand.
              </p>
              <p>
                And because trust matters in DeFi, every single recommendation YieldSage produces is <strong className="text-white">permanently recorded on the Mantle blockchain</strong> with a cryptographic fingerprint. Anyone can verify, at any time, that the recommendation was real and was never edited after the fact.
              </p>

              <Callout type="tip" title="Watch the Video Demo">
                Prefer a visual walkthrough? Watch our 13-minute <a href="https://www.youtube.com/watch?v=aUnmj3e3mjA" target="_blank" rel="noopener noreferrer" className="text-[#00ff88] hover:underline font-semibold">YieldSage Video Demo on YouTube</a> to see the scrollytelling interface, dashboard analytics, on-chain proof verification, and Telegram bot in action.
              </Callout>
            </div>

            <div className="grid gap-4 grid-cols-1 sm:grid-cols-3 mt-8">
              {[
                { icon: <RefreshCw className="w-5 h-5" />, color: "rgba(0,255,136,", title: "Hourly Updates", desc: "Every hour, YieldSage queries on-chain data from all tracked Mantle protocols and refreshes every metric on the dashboard automatically." },
                { icon: <Cpu className="w-5 h-5" />, color: "rgba(99,179,237,", title: "AI-Powered Scoring", desc: "A multi-model AI cascade analyses every pool and produces ranked recommendations — categorised into Stable, Moderate, and Aggressive risk tiers." },
                { icon: <ShieldCheck className="w-5 h-5" />, color: "rgba(167,139,250,", title: "Verifiable On-Chain", desc: "Every recommendation is SHA-256 fingerprinted and committed to Mantle as a transaction. Zero trust required — you can verify everything yourself." },
              ].map(({ icon, color, title, desc }) => (
                <div
                  key={title}
                  className="rounded-2xl p-5 space-y-3"
                  style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}
                >
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${color}0.1)`, color: `${color}0.85)`, border: `1px solid ${color}0.2)` }}>
                    {icon}
                  </div>
                  <h4 className="text-sm font-semibold text-white">{title}</h4>
                  <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.45)" }}>{desc}</p>
                </div>
              ))}
            </div>

            <Callout type="tip" title="Who is YieldSage for?">
              YieldSage is built for anyone who holds crypto on Mantle — from complete beginners who just want to know the safest place to earn yield on their stablecoins, to experienced DeFi users who want a reliable daily signal without manually reading protocol documentation every morning. No technical knowledge is required to use the dashboard or the Telegram bot.
            </Callout>
          </section>

          {/* ══════════════ 2. HOW IT WORKS ══════════════ */}
          <section id="how-it-works" className="scroll-mt-32">
            <SectionHeader
              num="02"
              tag="End-to-End Flow"
              title="How YieldSage Works — From Start to Finish"
              sub="A complete walkthrough of everything that happens behind the scenes, every single hour."
            />

            <div className="space-y-2">
              <Step n={1} title="On-Chain Data is Collected — Every Hour">
                YieldSage runs a custom query against <strong>Dune Analytics</strong> — a powerful on-chain data platform — every single hour, 24 hours a day. This query pulls real, live data directly from Mantle's blockchain records: the APY of every major liquidity pool, how much money is locked in each pool (TVL), what the reward tokens are, and how each metric has changed over the past 1 day, 7 days, and 30 days. The system is engineered for high availability, with built-in rate-limit resilience ensuring data collection is never interrupted.
              </Step>

              <Step n={2} title="Protocols Are Auto-Registered in the Database">
                When a new pool or protocol appears in the data for the first time, YieldSage automatically registers it in the database — capturing its name, contract address, pool type, protocol logo, and a link to its app. This means the platform always stays up to date without any manual intervention. Existing protocols are also updated if their metadata changes (for example, if a new logo becomes available).
              </Step>

              <Step n={3} title="The AI Scoring Engine Analyses Everything">
                After fresh data arrives, the <strong>AI Scoring Engine</strong> gets to work. This is where YieldSage becomes more than just a data aggregator. The engine sends all the current yield data to a cascade of powerful AI models (explained in more detail in the Yield Intelligence section) and asks them to do several things:
                <ul className="list-disc pl-5 mt-2 space-y-1">
                  <li>Rank every pool by its risk-adjusted attractiveness</li>
                  <li>Categorise each pool as Stable, Moderate, or Aggressive</li>
                  <li>Write a plain-English explanation of why each top pick is recommended</li>
                  <li>Identify any pools that are particularly high-risk right now</li>
                  <li>Flag unusual yield spikes or TVL changes that deserve attention</li>
                </ul>
              </Step>

              <Step n={4} title="Recommendations Are Fingerprinted and Committed On-Chain">
                Before any recommendation is stored in the database or shown to users, it is <strong>cryptographically fingerprinted</strong>. The entire recommendation — the protocol name, pool address, APY, AI reasoning, risk tier, and timestamp — is serialised into a standardised JSON format and then run through the SHA-256 hashing algorithm. The resulting hash (a unique 64-character string) is embedded into a 0-value transaction on the Mantle blockchain, making the recommendation permanently and publicly verifiable. This is explained in full detail in the On-Chain Proof section.
              </Step>

              <Step n={5} title="The Dashboard Updates Automatically">
                Once the new data and recommendations are stored, the web dashboard reflects them immediately. Every metric — APY, TVL, trends, risk tiers, recommendation cards — is live and sourced directly from the database. The dashboard refreshes automatically; you don't need to reload the page.
              </Step>

              <Step n={6} title="Personalised Alerts Are Sent via Telegram">
                Simultaneously, the <strong>Telegram bot</strong> sends personalised hourly updates to every user who has enabled alerts. Each update is tailored to the user's <strong>risk preference</strong> (Stable, Moderate, or Aggressive) and takes into account any paper trades they currently have open — so if a better opportunity has emerged within their risk tier, they're told about it immediately.
              </Step>
            </div>

            {/* Architecture flow diagram */}
            <div className="mt-8 p-6 rounded-2xl border space-y-4 overflow-x-auto" style={{ background: "rgba(0,0,0,0.5)", borderColor: "rgba(255,255,255,0.07)" }}>
              <p className="text-[10px] font-mono uppercase tracking-widest" style={{ color: "rgba(255,255,255,0.3)" }}>System Architecture — Data Flow</p>
              <div className="hidden sm:flex flex-col items-center gap-4 font-mono text-[10px] min-w-[500px]">
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)", color: "rgba(16,185,129,0.85)" }}>Mantle Network (On-Chain)</span>
                  <span style={{ color: "rgba(255,255,255,0.2)" }}>→</span>
                  <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(6,182,212,0.1)", border: "1px solid rgba(6,182,212,0.2)", color: "rgba(6,182,212,0.85)" }}>Dune Analytics API</span>
                  <span style={{ color: "rgba(255,255,255,0.2)" }}>→</span>
                  <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(6,182,212,0.1)", border: "1px solid rgba(6,182,212,0.2)", color: "rgba(6,182,212,0.85)" }}>DuneFetcher (Python)</span>
                </div>
                <div style={{ color: "rgba(255,255,255,0.2)" }}>↓</div>
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1.5 rounded-lg flex items-center gap-1.5" style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)", color: "rgba(59,130,246,0.85)" }}>
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" /> Supabase PostgreSQL
                  </span>
                </div>
                <div style={{ color: "rgba(255,255,255,0.2)" }}>↓ Simultaneously feeds ↓</div>
                <div className="flex items-center gap-6">
                  <div className="flex flex-col items-center gap-2">
                    <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)", color: "rgba(245,158,11,0.85)" }}>AI Scoring Engine</span>
                    <div style={{ color: "rgba(255,255,255,0.2)" }}>↓</div>
                    <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(0,255,136,0.1)", border: "1px solid rgba(0,255,136,0.2)", color: "rgba(0,255,136,0.85)" }}>SHA-256 + Mantle TX</span>
                  </div>
                  <div style={{ color: "rgba(255,255,255,0.2)" }}>|</div>
                  <div className="flex flex-col items-center gap-2">
                    <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(168,85,247,0.1)", border: "1px solid rgba(168,85,247,0.2)", color: "rgba(168,85,247,0.85)" }}>FastAPI Backend</span>
                    <div style={{ color: "rgba(255,255,255,0.2)" }}>↓</div>
                    <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(0,255,136,0.1)", border: "1px solid rgba(0,255,136,0.2)", color: "rgba(0,255,136,0.85)" }}>Next.js Dashboard</span>
                  </div>
                  <div style={{ color: "rgba(255,255,255,0.2)" }}>|</div>
                  <div className="flex flex-col items-center gap-2">
                    <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(236,72,153,0.1)", border: "1px solid rgba(236,72,153,0.2)", color: "rgba(236,72,153,0.85)" }}>Telegram Bot</span>
                    <div style={{ color: "rgba(255,255,255,0.2)" }}>↓</div>
                    <span className="px-3 py-1.5 rounded-lg" style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.5)" }}>Your Device</span>
                  </div>
                </div>
              </div>
              {/* Mobile simplified */}
              <div className="sm:hidden flex flex-col items-center gap-3 font-mono text-[10px]">
                {["Mantle Network", "Dune Analytics", "Supabase Database", "AI Scoring + On-Chain Hash", "Dashboard · Telegram · Alerts"].map((item, i, arr) => (
                  <div key={item} className="flex flex-col items-center gap-1 w-full">
                    <span className="px-3 py-1.5 rounded-lg text-center w-full" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.6)" }}>{item}</span>
                    {i < arr.length - 1 && <span style={{ color: "rgba(255,255,255,0.2)" }}>↓</span>}
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ══════════════ 3. DASHBOARD ══════════════ */}
          <section id="dashboard" className="scroll-mt-32">
            <SectionHeader
              num="03"
              tag="Dashboard Guide"
              title="Understanding the YieldSage Dashboard"
              sub="A complete guide to every section of the dashboard and how to use it effectively."
            />

            <div className="space-y-8 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.6)" }}>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The Overview Stats Bar</h3>
                <p className="mb-3">
                  At the top of the dashboard you'll find four headline numbers. These give you an instant pulse-check of the Mantle DeFi ecosystem right now:
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { label: "Protocols Tracked", color: "rgba(0,255,136,", desc: "The number of distinct DeFi protocols currently being monitored by YieldSage. Each protocol may have multiple pools." },
                    { label: "Pools Tracked", color: "rgba(99,179,237,", desc: "The total number of individual liquidity pools across all protocols. Each pool has its own APY, TVL, and risk profile." },
                    { label: "Total TVL", color: "rgba(246,173,85,", desc: "The combined value of all assets locked across every tracked pool, in USD. This represents how much money the ecosystem is managing." },
                    { label: "Avg APY", color: "rgba(167,139,250,", desc: "The average annual percentage yield across all tracked pools right now. Use this as a baseline when evaluating individual opportunities." },
                  ].map(({ label, color, desc }) => (
                    <div key={label} className="rounded-xl p-4 space-y-2" style={{ background: `${color}0.05)`, border: `1px solid ${color}0.15)` }}>
                      <div className="text-[10px] font-mono uppercase tracking-wider" style={{ color: `${color}0.7)` }}>{label}</div>
                      <div className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.4)" }}>{desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The AI Recommendation Cards</h3>
                <p className="mb-3">
                  Below the stats bar, you'll find the <strong className="text-white">AI Recommendation Cards</strong> — three cards, one for each risk tier (Stable, Moderate, Aggressive). Each card shows you the AI's current top pick within that tier, including:
                </p>
                <ul className="list-disc pl-5 space-y-1.5 mb-3">
                  <li><strong className="text-white">The protocol and pool name</strong> — what it is and where the yield comes from</li>
                  <li><strong className="text-white">The current APY</strong> — the annual percentage yield at the time of the last AI scoring run</li>
                  <li><strong className="text-white">The AI's reasoning</strong> — a plain-English paragraph written by the AI explaining why this pool is the best pick right now within this risk tier, and any caveats you should be aware of</li>
                  <li><strong className="text-white">An Invest link</strong> — takes you directly to the protocol's app where you can deploy capital</li>
                  <li><strong className="text-white">A Simulate button</strong> — lets you open a paper trade in the Telegram bot without committing real funds</li>
                </ul>
                <Callout type="info" title="What does 'current top pick' mean?">
                  The AI runs every hour. The recommendation you see is the AI's most recent assessment — not a historical suggestion. If the market moves significantly between runs, the next hourly update will reflect that change.
                </Callout>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The Leaderboard Table</h3>
                <p className="mb-3">
                  The main table shows every tracked pool ranked and filterable. Here's how to use it:
                </p>
                <ul className="list-disc pl-5 space-y-2">
                  <li><strong className="text-white">Sort any column</strong> by clicking the column header — click once for ascending, again for descending</li>
                  <li><strong className="text-white">Search</strong> by protocol name, pool name, or asset type using the search bar</li>
                  <li><strong className="text-white">Filter by risk tier</strong> using the toggle buttons (All / Stable / Moderate / Aggressive)</li>
                  <li><strong className="text-white">Filter by minimum TVL</strong> to exclude small pools with low liquidity</li>
                  <li><strong className="text-white">Add to Watchlist</strong> by clicking the star icon — watchlisted pools appear in your personal watchlist tab</li>
                  <li><strong className="text-white">Click the pool name</strong> to open its contract address on Mantlescan (the Mantle blockchain explorer)</li>
                  <li><strong className="text-white">Click Invest</strong> to go directly to the protocol's DApp to deposit funds</li>
                  <li><strong className="text-white">Click Simulate</strong> to run a paper trade through the Telegram bot</li>
                </ul>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The APY History Charts</h3>
                <p>
                  Below the leaderboard, you'll find interactive charts showing how the APY of each protocol has changed over the past 7 days (or 30 days — toggle between them). Select any protocol from the tabs above the chart to view its specific history. Hover over the chart to see the exact APY and timestamp for any point. These charts are useful for identifying whether a high APY is a stable trend or a temporary spike.
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The On-Chain Proof Section</h3>
                <p>
                  At the bottom of the main page (accessible via <code className="text-xs font-mono text-cyan-400">/#on-chain-proof</code>), you'll find the complete historical log of every AI recommendation that has been committed to the Mantle blockchain. You can search this log by protocol name, pool name, contract address, or transaction hash. Each entry links directly to its Mantlescan transaction and its verification page — where you can independently confirm the recommendation was never altered.
                </p>
              </div>
            </div>
          </section>

          {/* ══════════════ 4. METRICS ══════════════ */}
          <section id="metrics" className="scroll-mt-32">
            <SectionHeader
              num="04"
              tag="Every Metric Explained"
              title="What Every Number on the Dashboard Means"
              sub="Click any metric below for a detailed explanation of what it is, why it matters, and how to interpret it."
            />

            <div className="space-y-3">
              <MetricCard
                label="APY — Annual Percentage Yield"
                abbr="APY"
                color="rgba(0,255,136,0.9)"
                example="18.42%"
                description="APY is the projected annual return you would earn if you deposited funds into this pool today and left them for one full year. It accounts for the compounding of rewards over time. A pool showing 18.42% APY means that for every $1,000 you deposit, you would theoretically earn approximately $184.20 over 12 months — assuming the yield stays constant."
                detail="Important caveat: APY is never guaranteed in DeFi. Yields fluctuate constantly based on how much liquidity is in the pool, how much trading activity is happening, and what the protocol's reward emission rate is. A high APY today may be lower tomorrow. YieldSage tracks APY changes over 1D, 7D, and 30D periods to help you assess whether a yield is trending up or down."
              />
              <MetricCard
                label="Base APY"
                color="rgba(99,179,237,0.9)"
                example="6.84%"
                description="The Base APY is the portion of the yield that comes from actual trading fees generated by the pool — money paid by traders who use the pool to swap tokens. This is the most stable and reliable part of a pool's yield. It doesn't depend on any special reward programme; it simply comes from real economic activity."
                detail="A pool with a high Base APY relative to its total APY is generally considered healthier — it means the yield is supported by genuine demand, not just temporary incentives. When evaluating a pool's long-term sustainability, the Base APY is the number to focus on."
              />
              <MetricCard
                label="Reward APY"
                color="rgba(246,173,85,0.9)"
                example="11.58%"
                description="The Reward APY is the additional yield paid by the protocol in the form of its own reward tokens — on top of the trading fees. Protocols use reward emissions to attract liquidity to their pools, especially when they're new or want to incentivise specific trading pairs. This part of the yield can be very high, but it's also the most volatile."
                detail="Reward APY depends on the value of the reward token and how many tokens the protocol is distributing. If the reward token's price drops, the Reward APY drops too — even if nothing else changes. YieldSage's AI factors this dynamic into its risk assessment. A pool where 90% of its APY comes from rewards and only 10% from fees carries significantly more risk than one where that ratio is reversed."
              />
              <MetricCard
                label="TVL — Total Value Locked"
                abbr="TVL"
                color="rgba(167,139,250,0.9)"
                example="$4,200,000"
                description="TVL is the total dollar value of all assets deposited in a pool at any given moment. It tells you how large and liquid the pool is. A pool with $4.2M TVL has $4.2 million worth of tokens providing liquidity for traders."
                detail="TVL is one of the most important safety signals in DeFi. Very low TVL pools (under $100K) can be dangerous for several reasons: they're more vulnerable to price manipulation, your own deposit would represent a large percentage of the pool which creates slippage, and they may be too new to have a track record. YieldSage's risk tier system accounts for TVL — most Stable picks have significantly higher TVL than Aggressive ones."
              />
              <MetricCard
                label="Reward Tokens"
                color="rgba(236,72,153,0.9)"
                example="MNT, USDC"
                description="This shows the specific token(s) you receive as rewards for providing liquidity to this pool. For example, 'MNT' means the protocol pays you in MNT (Mantle's native token). Some pools pay rewards in multiple tokens simultaneously."
                detail="The identity of the reward token matters because you need to understand what you're receiving. Native tokens like MNT have established markets and liquidity. Newly launched protocol tokens may be harder to sell and more volatile. When evaluating a reward APY, always consider the market depth and price history of the reward token itself."
              />
              <MetricCard
                label="APY 1D / APY 7D / APY 30D — Trend Indicators"
                color="rgba(0,255,136,0.6)"
                example="+2.3% / -1.1% / +5.8%"
                description="These three numbers show how the pool's APY has changed over the past 1 day, 7 days, and 30 days. A positive number means the yield has been rising; a negative number means it's been falling. These trend indicators are colour-coded: green for rising, red for falling, grey for flat."
                detail="Trend data is critical for timing your entry into a pool. A pool with a currently attractive APY that has been declining for the past 30 days may not be the best choice. Conversely, a pool whose APY is trending upward may represent a better entry point than its current number suggests. YieldSage's AI weighs these trends when generating recommendations."
              />
              <MetricCard
                label="Risk Tier — Stable / Moderate / Aggressive"
                color="rgba(246,173,85,0.9)"
                example="STABLE"
                description="Risk Tier is YieldSage's AI-assigned classification of how much risk is associated with providing liquidity to this pool. Stable pools use fully collateralised stablecoins (like USDC or USDT pairs) with high TVL and low yield volatility. Moderate pools involve assets like ETH or MNT with meaningful liquidity but some price exposure. Aggressive pools offer the highest yields but come with significant price risk, lower liquidity, or newer protocol status."
                detail="The risk tier is not just about the tokens in the pool — it also considers the pool's TVL, the protocol's track record, the ratio of base APY to reward APY, and any unusual trends in the data. A stablecoin pool with very low TVL might still be classified as Moderate rather than Stable due to liquidity risk."
              />
              <MetricCard
                label="Protocol Image Placeholder"
                color="rgba(255,255,255,0.5)"
                example="🔷 M · A · G"
                description="Each protocol in the leaderboard has a logo image. If the official logo is available, it's displayed. If not, YieldSage generates a colour-coded letter avatar based on the protocol's name — this is the protocol icon placeholder you see."
                detail="The gradient colour of the placeholder icon is deterministically generated from the protocol name, so the same protocol always gets the same colour. This makes it easy to visually identify protocols even when their official logos aren't available yet."
              />
              <MetricCard
                label="Pool Contract Link"
                color="rgba(0,255,136,0.7)"
                example="https://mantlescan.xyz/address/0x..."
                description="Clicking the protocol name in the leaderboard opens the pool's smart contract address on Mantlescan — Mantle's blockchain explorer. This lets you independently verify that the pool exists on-chain, see its transaction history, and inspect its code."
                detail="Always clicking through to verify the contract address is a best practice in DeFi before depositing funds. A legitimate protocol will always have a verifiable on-chain contract address. YieldSage links directly to Mantlescan for transparency."
              />
            </div>
          </section>

          {/* ══════════════ 5. AI INTELLIGENCE ══════════════ */}
          <section id="ai-intel" className="scroll-mt-32">
            <SectionHeader
              num="05"
              tag="Yield Intelligence"
              title="How the AI Understands and Ranks Yield Opportunities"
              sub="A deep dive into how YieldSage's artificial intelligence actually works — with no technical jargon."
            />

            <div className="space-y-6 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.6)" }}>
              <p>
                The core of YieldSage is its <strong className="text-white">AI Scoring Engine</strong> — a system that doesn't just look at raw numbers, but actually reasons about what those numbers mean. Here's how it works, explained in plain English.
              </p>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">What Information Does the AI Receive?</h3>
                <p className="mb-3">Every hour, after the fresh data has been fetched, the AI Scoring Engine receives a comprehensive snapshot of all currently active pools. For each pool, the AI can see:</p>
                <ul className="list-disc pl-5 space-y-1.5">
                  <li>The current total APY and how it breaks down into base fees vs reward emissions</li>
                  <li>The pool's TVL and whether it has been growing or shrinking</li>
                  <li>APY trends over 1 day, 7 days, and 30 days</li>
                  <li>Which tokens are in the pool and what rewards are offered</li>
                  <li>The protocol name and its on-chain contract address</li>
                  <li>Comparative data across all other pools (so it can contextualise)</li>
                </ul>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The Multi-Model Cascade — Why YieldSage Never Goes Offline</h3>
                <p className="mb-3">
                  YieldSage doesn't depend on a single AI provider. Instead, it uses a <strong className="text-white">cascading provider system</strong> — a series of AI models from different companies, ordered by preference. When the Scoring Engine needs to generate recommendations, it tries them in this order:
                </p>
                <ol className="list-none space-y-2">
                  {[
                    { n: "1", name: "Cerebras (Llama 3.1 70B)", color: "rgba(0,255,136,0.85)", why: "Primary pipeline — chosen for maximum speed, completing each scoring run in seconds." },
                    { n: "2", name: "SambaNova (Llama 3.1 405B)", color: "rgba(99,179,237,0.85)", why: "Fallback 1 — one of the largest open-source models available, with exceptional reasoning depth." },
                    { n: "3", name: "Groq (GPT-OSS 120B / Qwen 3.6 27B)", color: "rgba(167,139,250,0.85)", why: "Fallback 2 — ultra-low latency inference with consistently reliable outputs." },
                    { n: "4", name: "NVIDIA NIM (Llama 3 70B)", color: "rgba(246,173,85,0.85)", why: "Fallback 3 — enterprise-grade cloud compute with high reliability." },
                    { n: "5", name: "Google Gemini Flash 1.5", color: "rgba(236,72,153,0.85)", why: "Ultimate fallback — Google's proprietary model, always available as a last resort." },
                  ].map(({ n, name, color, why }) => (
                    <li key={n} className="flex items-start gap-3 p-3 rounded-xl" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                      <span className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold font-mono flex-shrink-0 mt-0.5" style={{ background: `${color.replace(")", ",0.1)")}`, border: `1px solid ${color.replace(")", ",0.25)")}`, color }}>
                        {n}
                      </span>
                      <div>
                        <div className="text-xs font-semibold" style={{ color }}>{name}</div>
                        <div className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>{why}</div>
                      </div>
                    </li>
                  ))}
                </ol>
                <p className="mt-3">
                  If the first provider is unavailable or slow, the system immediately tries the next one — automatically, without any interruption to users. This means YieldSage's recommendations keep running even if one AI provider has an outage.
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">What Does the AI Actually Think About?</h3>
                <p className="mb-3">The AI is given a structured prompt that instructs it to evaluate each pool across several dimensions. It is specifically guided to:</p>
                <ul className="list-disc pl-5 space-y-2">
                  <li><strong className="text-white">Assess risk holistically</strong> — not just based on the tokens, but considering TVL depth, the proportion of reward vs fee yield, and trend stability</li>
                  <li><strong className="text-white">Consider sustainability</strong> — a 500% APY that comes entirely from reward emissions that are dropping fast is flagged differently than a 15% APY that comes from real trading fees</li>
                  <li><strong className="text-white">Rank within tiers, not globally</strong> — the Stable tier's top pick is the best option for risk-averse capital, not compared to Aggressive picks</li>
                  <li><strong className="text-white">Write honest, nuanced reasoning</strong> — the AI is instructed to acknowledge risks and caveats, not just cheerfully recommend everything</li>
                  <li><strong className="text-white">Account for comparative context</strong> — "18% APY is good" means something different if every other pool is at 30%</li>
                </ul>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">Dashboard AI Picks vs Personalised Alerts — What's the Difference?</h3>
                <p>
                  YieldSage generates two types of AI output every hour:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                  <div className="rounded-xl p-4 space-y-2" style={{ background: "rgba(0,255,136,0.04)", border: "1px solid rgba(0,255,136,0.12)" }}>
                    <h4 className="text-xs font-bold uppercase tracking-wider font-mono" style={{ color: "rgba(0,255,136,0.8)" }}>Dashboard Picks</h4>
                    <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.5)" }}>
                      The three recommendation cards shown on the web dashboard. These are market-wide — the best opportunity across all protocols for each risk tier, displayed identically to every visitor.
                    </p>
                  </div>
                  <div className="rounded-xl p-4 space-y-2" style={{ background: "rgba(167,139,250,0.04)", border: "1px solid rgba(167,139,250,0.12)" }}>
                    <h4 className="text-xs font-bold uppercase tracking-wider font-mono" style={{ color: "rgba(167,139,250,0.8)" }}>Personalised Telegram Alerts</h4>
                    <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.5)" }}>
                      Sent individually to each user based on their risk preference. The AI also considers your active paper trades — if a better opportunity has appeared within your risk tier since you last entered a trade, it highlights the switch. No two users receive the exact same alert.
                    </p>
                  </div>
                </div>
              </div>

              <Callout type="warning" title="This is not financial advice">
                YieldSage is an intelligence tool, not a financial advisor. The AI's reasoning reflects data analysis and pattern recognition — not regulated financial guidance. Always do your own research before depositing real funds into any DeFi protocol. Yields in DeFi carry real risks including smart contract vulnerabilities, liquidation risk, and market volatility.
              </Callout>
            </div>
          </section>

          {/* ══════════════ 6. ON-CHAIN PROOF ══════════════ */}
          <section id="onchain" className="scroll-mt-32">
            <SectionHeader
              num="06"
              tag="Verifiability"
              title="On-Chain Proof — How YieldSage Earns Your Trust"
              sub="The complete technical explanation of how every recommendation is permanently verified on the Mantle blockchain — explained so anyone can understand it."
            />

            <div className="space-y-6 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.6)" }}>

              <p>
                YieldSage makes a bold claim: every AI recommendation it has ever produced is verifiable, immutable, and publicly accessible to anyone, forever. Here's exactly how that works.
              </p>

              <div>
                <h3 className="text-base font-semibold text-white mb-4">The Problem: How Do You Know the AI Said That?</h3>
                <p>
                  Imagine an AI system that tells you a pool is a great investment today, but then the pool performs badly. In a traditional system, the company could quietly edit or delete the recommendation — and you'd have no way to prove it ever existed. This is a fundamental trust problem. YieldSage solves it by making every recommendation impossible to alter after it's created.
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-4">Step 1 — Building the Canonical Payload</h3>
                <p className="mb-3">
                  When the AI produces a recommendation, YieldSage assembles all of the important data into a single structured document called the <strong className="text-white">canonical payload</strong>. "Canonical" means it's always assembled in exactly the same way — same field names, same order, same formatting rules — regardless of when or where it's created. This payload includes:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    ["version", "The schema version (e.g. 1.0) to ensure future changes don't break verification"],
                    ["scored_at", "The exact UTC timestamp when the AI ran — set before the model is called"],
                    ["protocol_name", "The DeFi protocol name (e.g. Merchant Moe)"],
                    ["pool_name", "The specific pool (e.g. USDe-WMNT)"],
                    ["pool_address", "The on-chain contract address in lowercase"],
                    ["risk_tag", "The AI-assigned tier: stable, moderate, or aggressive"],
                    ["rank", "The position within this risk tier (1 = top pick)"],
                    ["apy_at_time", "The exact APY at the moment of scoring, stored as a 4-decimal string"],
                    ["tvl_usd", "The total value locked at scoring time, as a 2-decimal string"],
                    ["ai_reasoning", "The verbatim text of the AI's reasoning, trimmed of whitespace"],
                    ["ai_model", "The exact model identifier used (e.g. llama-3.1-70b)"],
                    ["chain", "Always 'mantle' for this version"],
                    ["chain_id", "Always 5000 — Mantle Network's numeric identifier"],
                    ["source", "The Dune query ID used as the data source"],
                  ].map(([field, desc]) => (
                    <div key={field} className="flex gap-2 text-xs p-2 rounded-lg" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)" }}>
                      <code className="font-mono flex-shrink-0" style={{ color: "rgba(0,255,136,0.7)" }}>{field}</code>
                      <span style={{ color: "rgba(255,255,255,0.35)" }}>{desc}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">Step 2 — The SHA-256 Fingerprint</h3>
                <p className="mb-3">
                  Once the payload is assembled, it's converted to a <strong className="text-white">canonical JSON string</strong> — all fields sorted alphabetically, no extra spaces, UTF-8 encoded. This string is then passed through the <strong className="text-white">SHA-256 hashing algorithm</strong>.
                </p>
                <p className="mb-3">
                  SHA-256 is a cryptographic function that takes any piece of data and produces a unique 64-character string called a <strong className="text-white">hash</strong> or <strong className="text-white">fingerprint</strong>. The most important property of SHA-256 is this:
                </p>
                <Callout type="important" title="The One-Way Guarantee">
                  Change even a single character in the original data — a space, a capital letter, one digit in the APY — and the resulting hash changes completely and unpredictably. You cannot reverse-engineer the original data from the hash alone. This means: if the hash matches, the data is 100% identical to what was originally fingerprinted. No exceptions.
                </Callout>
                <p>
                  The hash looks something like this: <code className="text-xs font-mono" style={{ color: "rgba(0,255,136,0.8)" }}>a3f6d192b5e8c041...</code> (64 hex characters total). This is the recommendation's digital fingerprint.
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">Step 3 — Embedding the Hash in a Mantle Transaction</h3>
                <p className="mb-3">
                  The hash is then prefixed with a YieldSage identifier: <code className="text-xs font-mono" style={{ color: "rgba(0,255,136,0.8)" }}>yieldsage:{"<hash>"}</code>. This string is embedded as the <strong className="text-white">data field</strong> of a transaction on the Mantle blockchain.
                </p>
                <p className="mb-3">
                  The transaction is a self-transfer — it sends 0 MNT from YieldSage's wallet to itself. This means no funds move, and the transaction's only purpose is to record the hash on the blockchain. Once the transaction is confirmed (which takes seconds on Mantle), the hash is <strong className="text-white">permanently, publicly, and immutably recorded</strong>. The Mantle blockchain is a public ledger — anyone in the world can see this transaction, forever.
                </p>
                <p>
                  The system includes retry logic: if the first attempt to submit the transaction fails (due to network congestion or an RPC issue), it automatically retries up to 3 times with increasing delays. If the transaction still fails after all retries, the hash is still stored in the database — and a background job runs every 6 hours to retry any recommendations that haven't yet been committed to the chain.
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">Step 4 — Verifying in Your Own Browser</h3>
                <p className="mb-3">
                  The <strong className="text-white">Proof Verification page</strong> (<code className="text-xs font-mono text-cyan-400">/verify?tx={"<transaction hash>"}</code>) lets you independently verify any recommendation without trusting YieldSage at all. Here's what happens when you open it:
                </p>
                <ol className="list-none space-y-3">
                  {[
                    { n: 1, t: "YieldSage fetches the original recommendation from the database", d: "This includes the complete canonical payload exactly as it was assembled before hashing." },
                    { n: 2, t: "The canonical JSON string is rebuilt locally in your browser", d: "The same serialisation logic runs client-side — sorted fields, no extra whitespace." },
                    { n: 3, t: "Your browser computes the SHA-256 hash independently", d: "Using the Web Crypto API — a standard browser feature. YieldSage's servers play no role in this step." },
                    { n: 4, t: "The computed hash is compared to the one stored in the database", d: "If they match: Perfect Match. The data is identical to what was originally fingerprinted. If they don't: the data has been altered." },
                  ].map(({ n, t, d }) => (
                    <li key={n} className="flex gap-4 p-4 rounded-xl" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                      <span className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold font-mono flex-shrink-0 mt-0.5" style={{ background: "rgba(0,255,136,0.1)", border: "1px solid rgba(0,255,136,0.2)", color: "rgba(0,255,136,0.85)" }}>{n}</span>
                      <div>
                        <div className="text-sm font-medium text-white mb-1">{t}</div>
                        <div className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>{d}</div>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">Why This Matters</h3>
                <p>
                  This system means that YieldSage cannot retroactively change or delete any recommendation. If it tried to alter a recommendation in the database, the hash would no longer match — and anyone who visits the verification page would immediately see <strong className="text-white">"Hash Mismatch — Tampered!"</strong>. The blockchain record is the source of truth, and the blockchain is controlled by nobody — it's a global public ledger that will exist for as long as Mantle Network exists.
                </p>
                <p className="mt-3">
                  This is what <em>trustless verifiability</em> means: you don't have to trust YieldSage. You can verify everything yourself.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <a
                  href="/#on-chain-proof"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all"
                  style={{ background: "rgba(0,255,136,0.1)", border: "1px solid rgba(0,255,136,0.2)", color: "rgba(0,255,136,0.9)" }}
                >
                  <ShieldCheck className="w-4 h-4" />
                  View Historical On-Chain Proofs
                </a>
                <a
                  href="https://mantlescan.xyz"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.5)" }}
                >
                  <ExternalLink className="w-4 h-4" />
                  Mantlescan Explorer
                </a>
              </div>
            </div>
          </section>

          {/* ══════════════ 7. TELEGRAM BOT ══════════════ */}
          <section id="telegram" className="scroll-mt-32">
            <SectionHeader
              num="07"
              tag="Telegram Bot"
              title="The YieldSage Telegram Bot — Your DeFi Assistant"
              sub="Everything you can do with @YieldSageBot and how to get the most out of it."
            />

            <div className="space-y-6 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.6)" }}>
              <p>
                The Telegram bot at <a href="https://t.me/YieldSageBot" target="_blank" rel="noopener noreferrer" className="text-[#00ff88] hover:underline">t.me/YieldSageBot</a> is your real-time DeFi assistant. It runs 24/7, responds to your commands within seconds, and proactively alerts you when the market changes in ways that matter to your portfolio. You don't need to have the website open — the bot brings the intelligence directly to your phone.
              </p>

              <div>
                <h3 className="text-base font-semibold text-white mb-4">Available Commands</h3>
                <div className="divide-y" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                  <CommandPill cmd="/start" desc="Registers your account and shows the main interactive menu with buttons for all key features. This is the first command to run." />
                  <CommandPill cmd="/yields" desc="Displays a paginated, scrollable view of all current yield opportunities across every tracked Mantle protocol. Tap Next/Prev to navigate pages." />
                  <CommandPill cmd="/trade" desc="Opens the paper trading flow. You can select a pool from the paginated list, specify how much USD to simulate investing, and the bot records the trade on your profile." />
                  <CommandPill cmd="/positions" desc="Shows all your currently active paper trades with their entry APY, the current APY, the simulated profit or loss, and how long each has been open." />
                  <CommandPill cmd="/alerts" desc="Toggles your hourly alert subscription on or off. When on, you receive a personalised market update every hour — tailored to your risk preference." />
                  <CommandPill cmd="/risk" desc="Changes your risk preference between Stable, Moderate, and Aggressive. This affects which recommendations appear in your personalised alerts." />
                  <CommandPill cmd="/prompts" desc="Lazy to think of prompts? This command shows you the best prompts to use with the bot." />
                  <CommandPill cmd="/verify" desc="Verify yield data by providing a pool address and clicking on the Verify button." />
                  <CommandPill cmd="/help" desc="Get help with using the bot." />
                </div>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The Simulate Feature — Paper Trading from the Web Dashboard</h3>
                <p className="mb-3">
                  Any pool visible on the YieldSage web dashboard has a <strong className="text-white">Simulate</strong> button. When you click it, a dialog appears asking how much USD you want to simulate investing. After you enter an amount and click Approve, your browser opens Telegram with a pre-filled command that looks like this:
                </p>
                <div className="p-4 rounded-xl font-mono text-xs" style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(0,255,136,0.15)", color: "rgba(0,255,136,0.85)" }}>
                  /trade address=0x5d54d430d1fd9425976147318e6080479bffc16d amount=10000 token=merchant-moe (USDe-WMNT)
                </div>
                <p className="mt-3">
                  The bot reads the pool contract address directly from this command, looks up its current APY, and records the paper trade instantly — no need to navigate any menus. The pool address is extracted from the command or from the full Mantlescan URL (either format works).
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">Personalised Hourly Alerts — What They Include</h3>
                <p className="mb-3">
                  When alerts are enabled, you receive a message every hour that includes:
                </p>
                <ul className="list-disc pl-5 space-y-1.5">
                  <li>The current best opportunity within your chosen risk tier, with the AI's reasoning</li>
                  <li>A comparison of where you are vs where you could be (if you have active paper trades)</li>
                  <li>Any significant APY changes across all pools since the last update</li>
                  <li>A one-line market summary (e.g., "Stable yields rose 2% on average this hour as liquidity shifted")</li>
                </ul>
                <Callout type="tip" title="Pro tip: Use /alerts to manage notification fatigue">
                  If hourly alerts feel like too much, you can disable them at any time with /alerts and re-enable them when you're ready to actively monitor the market. Your paper trade positions remain active regardless.
                </Callout>
              </div>
            </div>
          </section>

          {/* ══════════════ 8. DATA PIPELINE ══════════════ */}
          <section id="pipeline" className="scroll-mt-32">
            <SectionHeader
              num="08"
              tag="Data Pipeline"
              title="How YieldSage Collects and Processes On-Chain Data"
              sub="A transparent explanation of where the data comes from and how it gets into your dashboard."
            />

            <div className="space-y-6 text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.6)" }}>
              <div>
                <h3 className="text-base font-semibold text-white mb-3">The Data Source: Dune Analytics</h3>
                <p className="mb-3">
                  YieldSage pulls all of its yield data from <strong className="text-white">Dune Analytics</strong> — a professional on-chain data platform that allows developers to write custom SQL queries against raw blockchain data. This approach means the data comes directly from Mantle's on-chain records, not from any protocol's own self-reported API (which could be manipulated or delayed).
                </p>
                <p>
                  YieldSage maintains a custom Dune query (Query ID: <code className="text-xs font-mono text-cyan-400">7595582</code>) that extracts the following for every active Mantle liquidity pool: pool address, protocol name, asset pair, current APY, base APY, reward APY, TVL in USD, reward tokens, and 1D/7D/30D APY trends.
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The Fetching Cycle — Every Hour, Without Fail</h3>
                <p className="mb-3">
                  The fetching system is built for reliability. Every hour:
                </p>
                <ol className="list-decimal pl-5 space-y-2">
                  <li>The scheduler validates the active API key's credit balance and selects the next available key if needed</li>
                  <li>The query is executed on Dune — Dune runs the SQL against the latest blockchain data</li>
                  <li>The system monitors the execution status and waits for completion</li>
                  <li>The results are downloaded as a CSV file</li>
                  <li>The CSV is parsed and each row is matched to an existing protocol in the database (or a new protocol is created if it's new)</li>
                  <li>A new yield snapshot is inserted for each pool — a timestamped record of all metrics at this exact moment</li>
                  <li>The active key is cycled forward to distribute load across the next scheduled run</li>
                </ol>
                <p className="mt-3">
                  If a query execution fails, the system does not give up. It retries the execution up to 30 times within the same trial, waiting 15 seconds between each attempt and continuously monitoring the query status until it either completes or exhausts all attempts. If all 30 attempts within a trial fail, the system resets and begins a fresh trial — up to 3 trials in total. This means the fetcher makes up to 90 total execution attempts before a fetch session is considered failed. At the start of each new trial, the system validates the active key's credit balance and rotates to the next available key if needed. If all 3 trials are exhausted, the previous data remains visible on the dashboard — it is never wiped — and the next scheduled hourly run starts the entire process fresh.
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">Protocol Auto-Registration</h3>
                <p>
                  When a new protocol or pool appears in the Dune data for the first time, YieldSage automatically creates a record for it in the database. The system intelligently infers the initial risk tier: pools containing stablecoin assets (USDC, USDT, DAI, USDB, etc.) are initially classified as Stable, while everything else starts as Moderate. The AI Scoring Engine may override this classification based on further analysis.
                </p>
              </div>

              <div>
                <h3 className="text-base font-semibold text-white mb-3">The Database — Your Data, Always Available</h3>
                <p>
                  All data is stored in <strong className="text-white">Supabase</strong> — a managed PostgreSQL database with enterprise-grade reliability. The key tables are:
                </p>
                <div className="grid gap-3 mt-4">
                  {[
                    { table: "protocols", color: "rgba(0,255,136,", desc: "One record per unique pool — stores the protocol name, pool name, contract address, risk tier, logo URL, and app link." },
                    { table: "yield_snapshots", color: "rgba(99,179,237,", desc: "A time-series of all metrics for every pool, with a new row inserted every hour. This powers the APY history charts." },
                    { table: "recommendations", color: "rgba(167,139,250,", desc: "Every AI recommendation ever generated — with the AI reasoning, APY at time, risk tier, and the on-chain transaction hash for verification." },
                    { table: "paper_trades", color: "rgba(246,173,85,", desc: "Each user's simulated trades, recording the entry APY, entry amount, and current status." },
                    { table: "telegram_messages", color: "rgba(236,72,153,", desc: "A log of every message sent or queued for delivery via the Telegram bot." },
                    { table: "alert_preferences", color: "rgba(255,255,255,", desc: "Per-user alert settings — whether alerts are enabled and what thresholds trigger them." },
                  ].map(({ table, color, desc }) => (
                    <div key={table} className="flex gap-3 p-3 rounded-lg" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                      <code className="text-xs font-mono font-semibold flex-shrink-0 mt-0.5" style={{ color: `${color}0.8)` }}>{table}</code>
                      <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.45)" }}>{desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* ══════════════ 9. API REFERENCE ══════════════ */}
          <section id="api-ref" className="scroll-mt-32">
            <SectionHeader
              num="09"
              tag="API Reference"
              title="REST API Endpoints"
              sub="The public API endpoints used by the dashboard — open for developer access."
            />

            <div className="space-y-4">
              <Endpoint
                method="GET"
                path="/api/yields/leaderboard"
                desc="Returns paginated yield opportunities, filterable by risk, APY, and TVL"
                params={[
                  { name: "page", type: "integer", description: "Page number (default: 1)" },
                  { name: "page_size", type: "integer", description: "Results per page (default: 20, max: 100)" },
                  { name: "search", type: "string", description: "Filter by protocol name, pool name, or asset" },
                  { name: "risk_tag", type: "string", description: "Filter to a specific tier: stable, moderate, or aggressive" },
                  { name: "min_tvl", type: "number", description: "Minimum TVL in USD" },
                  { name: "min_apy", type: "number", description: "Minimum APY percentage" },
                  { name: "sort_by", type: "string", description: "Column to sort by: apy, tvl_usd, base_apy, reward_apy" },
                  { name: "sort_dir", type: "string", description: "Sort direction: asc or desc (default: desc)" },
                ]}
                example={`{
  "data": [
    {
      "protocol_id": "uuid",
      "asset": "USDe-WMNT",
      "apy": 18.42,
      "base_apy": 6.84,
      "reward_apy": 11.58,
      "tvl_usd": 4200000,
      "reward_tokens": "MNT",
      "apy_1d": 0.23,
      "apy_7d": -0.11,
      "apy_30d": 5.80,
      "protocol": {
        "name": "Merchant Moe",
        "pool_name": "USDe-WMNT",
        "pool_address": "0x5d54d...",
        "risk_tag": "moderate",
        "image_url": "https://...",
        "app_link": "https://..."
      }
    }
  ],
  "total": 152,
  "page": 1,
  "page_size": 20,
  "has_more": true
}`}
              />

              <Endpoint
                method="GET"
                path="/api/stats/overview"
                desc="Headline summary statistics for the dashboard overview cards"
                example={`{
  "protocols_tracked": 12,
  "pools_tracked": 152,
  "total_tvl": 45678239.12,
  "average_apy": 14.28,
  "median_apy": 8.52,
  "last_data_refresh": "2026-06-06T08:00:00.000Z"
}`}
              />

              <Endpoint
                method="GET"
                path="/api/recommendations/latest"
                desc="Returns the most recent AI recommendation for each risk tier"
                params={[
                  { name: "risk_tag", type: "string", description: "Filter by tier: stable, moderate, or aggressive. Omit for all three." },
                ]}
                example={`{
  "stable": {
    "protocol": { "name": "Agni Finance", "pool_name": "USDC-USDT" },
    "apy_at_time": 8.41,
    "risk_tag": "stable",
    "ai_reasoning": "This USDC/USDT pool...",
    "on_chain_tx_hash": "0xabc..."
  },
  "moderate": { ... },
  "aggressive": { ... }
}`}
              />

              <Endpoint
                method="GET"
                path="/api/recommendations/history"
                desc="Paginated historical log of all on-chain verified recommendations"
                params={[
                  { name: "page", type: "integer", description: "Page number (default: 1)" },
                  { name: "page_size", type: "integer", description: "Results per page (default: 8)" },
                ]}
              />

              <Endpoint
                method="GET"
                path="/api/recommendations/verify/{tx_hash}"
                desc="Returns the original payload and canonical JSON string for a given transaction hash, enabling browser-side SHA-256 verification"
                params={[
                  { name: "tx_hash", type: "string", required: true, description: "The Mantle transaction hash of the on-chain proof" },
                ]}
                example={`{
  "data": {
    "recommendation_hash": "a3f6d192...",
    "apy_at_time": 18.42,
    "risk_tag": "moderate",
    "on_chain_tx_hash": "0xabc...",
    "explorer_url": "https://mantlescan.xyz/tx/0xabc...",
    "protocols": { "name": "Merchant Moe", ... }
  },
  "canonical_payload": "{\"ai_model\":\"llama...\",\"ai_reasoning\":\"...\",..."
}`}
              />

              <Endpoint
                method="GET"
                path="/api/yields/history/{protocol_id}"
                desc="Time-series APY history for a specific protocol, used to power the APY charts"
                params={[
                  { name: "protocol_id", type: "uuid", required: true, description: "The protocol's database UUID" },
                  { name: "days", type: "integer", description: "Number of days of history (default: 7, max: 30)" },
                ]}
              />

              <Endpoint
                method="GET"
                path="/api/yields/watchlist"
                desc="Returns yield data for a list of specific protocol IDs (used for the watchlist feature)"
                params={[
                  { name: "ids", type: "string", required: true, description: "Comma-separated list of protocol UUIDs" },
                ]}
              />
            </div>

            <Callout type="info" title="Base URL">
              The API base URL resolves automatically based on environment. All endpoints support CORS and return JSON.
            </Callout>
          </section>

          {/* ══════════════ 10. FAQ ══════════════ */}
          <section id="faq" className="scroll-mt-32">
            <SectionHeader
              num="10"
              tag="FAQ"
              title="Frequently Asked Questions"
              sub="Answers to the most common questions about how YieldSage works."
            />

            <div className="space-y-3 max-w-3xl">
              <FAQ q="Does YieldSage ever execute trades or move my funds?">
                No. YieldSage is an <strong>intelligence and analytics platform</strong> — it never touches your crypto. It has no access to your wallet, cannot sign any transactions on your behalf, and does not connect to your wallet in any way. All trading decisions and fund movements are made by you, manually, through the protocol's own interface. YieldSage simply tells you where the best opportunities are.
              </FAQ>

              <FAQ q="Is YieldSage financial advice?">
                No. YieldSage is an information tool, not a regulated financial advisor. Everything on the platform — recommendations, risk tiers, AI reasoning — is for educational and informational purposes only. DeFi carries real risks. You should always do your own research and only invest what you can afford to lose. Nothing on YieldSage constitutes investment advice, and YieldSage bears no responsibility for financial decisions made based on its outputs.
              </FAQ>

              <FAQ q="How often is the data updated?">
                The data pipeline runs every hour, 24 hours a day. The APY and TVL figures you see on the dashboard are never more than one hour old. The AI Scoring Engine also runs every hour, immediately after the data fetch completes. This means the dashboard and bot recommendations reflect the current state of the market, not yesterday's numbers.
              </FAQ>

              <FAQ q="Why does the dashboard protocol count differ from the total number of rows?">
                The "Protocols Tracked" metric counts unique <em>protocol names</em> (e.g. Merchant Moe, Agni Finance, mETH Protocol). The "Pools Tracked" metric counts every individual liquidity pool. A single protocol can run many pools simultaneously — for example, Merchant Moe may operate dozens of different token pair pools at the same time. So you might see 12 protocols but 152 pools.
              </FAQ>

              <FAQ q="Why do TVL values sometimes differ from DefiLlama?">
                YieldSage pulls TVL data from Dune Analytics queries that focus on <em>active, high-liquidity yield opportunities</em>. Low-TVL or inactive pools may be filtered out by the Dune query. DefiLlama aggregates TVL across an entire protocol including inactive pools, locked positions, and other components. These differences are expected and don't indicate any inaccuracy in YieldSage's data.
              </FAQ>

              <FAQ q="What does the Risk Tier classification actually mean in practice?">
                <strong>Stable</strong> pools are almost entirely stablecoin-based (e.g. USDC/USDT). Price risk is minimal, TVL is usually high, and yield is modest but reliable. These are suitable for capital you can't afford to lose significant value on. <br /><br />
                <strong>Moderate</strong> pools typically involve a mix of stablecoins and volatile assets (e.g. ETH, MNT) or are stablecoin pools with lower TVL. There's some price exposure and the yield can fluctuate more. <br /><br />
                <strong>Aggressive</strong> pools have the highest potential yields but come with the most risk. They may involve newer tokens, lower liquidity, heavily reward-dependent yields, or protocols with shorter track records.
              </FAQ>

              <FAQ q="What is a paper trade? How does it work?">
                A paper trade is a <strong>simulated investment</strong> — you record a position as if you'd invested real money, but no actual funds are moved. YieldSage records the pool you chose, the APY at the time you entered, and the amount you simulated. You can then track how your simulated position performs over time: see if the APY went up or down, whether you would have profited, and how your pick compares to other pools. It's a risk-free way to test strategies and build confidence before committing real capital.
              </FAQ>

              <FAQ q="What is the Mantle Network? Why does YieldSage focus on it?">
                Mantle is a Layer 2 blockchain built on Ethereum — meaning it inherits Ethereum's security while offering much lower transaction fees and faster confirmation times. It has a growing DeFi ecosystem with multiple protocols offering competitive yields. YieldSage focuses on Mantle because it believes Mantle represents one of the most compelling emerging DeFi ecosystems, and because there's currently a gap: there's no intelligent, real-time yield aggregator specifically tailored to Mantle's unique protocol landscape.
              </FAQ>

              <FAQ q="Can I verify a recommendation even years later?">
                Yes. As long as the Mantle blockchain exists (and it's designed to exist permanently), the transaction containing the hash will be publicly accessible. The YieldSage database also retains all historical recommendations indefinitely. You can visit the /verify page with any historical transaction hash — from day 1 of YieldSage's operation — and verify it exactly as you would a recent one.
              </FAQ>

              <FAQ q="What happens if the AI provider has an outage?">
                YieldSage's multi-model cascade automatically handles this. If the primary AI provider (Cerebras) is unavailable, the system instantly tries SambaNova, then Groq, then NVIDIA NIM, then Google Gemini. In the extremely unlikely event that all five providers are unavailable simultaneously, the previous recommendations remain displayed on the dashboard with a "last updated X hours ago" indicator, and the system retries automatically on the next scheduled run.
              </FAQ>

              <FAQ q="How do I get started with the Telegram bot?">
                Simply open <a href="https://t.me/YieldSageBot" target="_blank" rel="noopener noreferrer" className="text-[#00ff88] hover:underline">t.me/YieldSageBot</a> in Telegram and type /start. The bot will register your account, show you the interactive menu, and ask for your risk preference. From that point, you can query for yield recommendations, set up alerts, and start paper trading — all from within Telegram with no technical knowledge required.
              </FAQ>

              <FAQ q="Is YieldSage open source?">
                The project is currently in active development. Follow the project's announcements for updates on open-source availability. The on-chain verification mechanism is fully transparent and auditable by anyone with a transaction hash — regardless of whether the codebase is publicly available.
              </FAQ>
            </div>
          </section>

        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-black/40 py-10 relative z-10 mt-16">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-12 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <img src="/logo.jpg" alt="YieldSage" className="w-6 h-6 rounded-md border border-white/10 object-cover" />
            <span className="text-[10px] font-mono text-white/20">YieldSage Docs — v1.2.0</span>
          </div>
          <div className="flex items-center gap-3 md:gap-4 text-xs font-mono text-white/40 flex-wrap justify-end">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <span>·</span>
            <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
            <span>·</span>
            <a href="https://www.youtube.com/watch?v=aUnmj3e3mjA" target="_blank" rel="noopener noreferrer" className="hover:text-[#00ff88] transition-colors">Video Demo</a>
            <span>·</span>
            <a href="https://t.me/YieldSageBot" target="_blank" rel="noopener noreferrer" className="hover:text-[#00ff88] transition-colors">Telegram Bot</a>
            <span>·</span>
            <Link href="/#on-chain-proof" className="hover:text-white transition-colors">On-Chain Proofs</Link>
            <span>·</span>
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy</Link>
            <span>·</span>
            <Link href="/cookies" className="hover:text-white transition-colors">Cookies</Link>
          </div>
        </div>
      </footer>

      <style dangerouslySetInnerHTML={{ __html: `
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .mask-fade-edges {
          mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
          -webkit-mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
        }
      `}} />
    </div>
  );
}
