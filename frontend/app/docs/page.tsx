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
  Code,
  Copy,
  Check
} from "lucide-react";

// Sections list for scroll spy navigation
const sections = [
  { id: "intro", label: "Introduction", icon: BookOpen },
  { id: "architecture", label: "Architecture", icon: Layers },
  { id: "pipeline", label: "Data Pipeline", icon: Database },
  { id: "ai-scorer", label: "AI Scorer", icon: Cpu },
  { id: "telegram", label: "Telegram Bot", icon: Bot },
  { id: "api-ref", label: "API Reference", icon: Terminal },
  { id: "faq", label: "FAQ", icon: HelpCircle },
];

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState("intro");
  const [scrollProgress, setScrollProgress] = useState(0);
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      const navHeight = 110; // offset for sticky dual nav header
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - navHeight;

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth"
      });
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(id);
    setTimeout(() => setCopiedText(null), 2000);
  };

  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current) return;
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? Math.min(scrollTop / docHeight, 1) : 0;
      setScrollProgress(progress);

      // Determine active section based on proximity
      const sectionElements = sections.map(s => document.getElementById(s.id));
      for (const el of sectionElements) {
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        if (rect.top <= window.innerHeight / 2 && rect.bottom >= window.innerHeight / 2) {
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
      {/* Interactive mouse background spotlight and noise grain */}
      <MouseGradientBackground />

      {/* Top Scroll Progress Bar */}
      <div className="fixed top-0 left-0 right-0 z-50 h-[2px] bg-white/5">
        <div
          className="h-full bg-gradient-to-r from-[#00ff88] to-cyan-400 transition-all duration-150"
          style={{ width: `${scrollProgress * 100}%` }}
        />
      </div>

      {/* Double Row Header Navigation */}
      <header className="sticky top-0 z-40 w-full border-b border-white/5 bg-black/50 backdrop-blur-xl">
        <div className="flex flex-col w-full max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-12 py-3 gap-3">
          
          {/* Top Row: Logo + Back button */}
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <img 
                src="/logo.jpg" 
                alt="YieldSage Logo" 
                className="w-7 h-7 rounded-lg border border-white/10 group-hover:border-[#00ff88]/50 object-cover transition-all"
              />
              <span className="font-sans font-light tracking-wider text-xs text-white/90 group-hover:text-white transition-colors">
                YIELD<span className="text-[#00ff88] font-medium font-mono">SAGE</span>
              </span>
              <span className="text-[9px] font-mono text-cyan-400 border border-cyan-500/30 px-1.5 py-0.5 rounded ml-1 bg-cyan-950/20">
                WHITEPAPER
              </span>
            </Link>

            <div className="flex items-center gap-4">
              <Link
                href="/dashboard"
                className="text-xs font-mono text-[#00ff88] hover:underline flex items-center gap-1"
              >
                Go to Dashboard
              </Link>
              <Link
                href="/"
                className="text-xs font-mono text-white/40 hover:text-white flex items-center gap-1 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back Home
              </Link>
            </div>
          </div>

          {/* Bottom Row: Scroll Spy Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1 mask-fade-edges scroll-smooth">
            {sections.map((section) => {
              const Icon = section.icon;
              const isActive = activeSection === section.id;
              return (
                <button
                  key={section.id}
                  onClick={() => scrollToSection(section.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-mono tracking-wide uppercase transition-all duration-300 whitespace-nowrap outline-none border ${
                    isActive
                      ? "text-[#00ff88] bg-[#00ff88]/10 border-[#00ff88]/30 shadow-[0_0_12px_rgba(0,255,136,0.05)]"
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

      {/* Main Content Layout */}
      <div className="relative z-10 w-full max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-12 py-12 grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-12 items-start">
        
        {/* Sidebar Index Links (Large Screens) */}
        <aside className="hidden lg:block sticky top-32 space-y-4">
          <p className="text-[10px] font-mono tracking-widest uppercase text-white/30 font-semibold px-2">
            Table of Contents
          </p>
          <nav className="flex flex-col gap-1.5">
            {sections.map((section) => {
              const isActive = activeSection === section.id;
              return (
                <button
                  key={section.id}
                  onClick={() => scrollToSection(section.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-all duration-200 border-l-2 ${
                    isActive
                      ? "text-[#00ff88] border-[#00ff88] bg-[#00ff88]/5 pl-4 font-semibold"
                      : "text-white/40 hover:text-white/80 border-transparent hover:border-white/10 pl-3"
                  }`}
                >
                  {section.label}
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Sections Content */}
        <div className="space-y-24">
          
          {/* 1. Introduction Section */}
          <section id="intro" className="space-y-6 scroll-mt-28">
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-[#00ff88] uppercase tracking-[0.2em]">01 / Introduction</span>
              <h2 className="text-3xl font-light tracking-tight font-sans">Yield Intelligence Protocol</h2>
            </div>
            <div className="text-sm text-white/60 leading-relaxed font-sans space-y-4 max-w-3xl">
              <p>
                <strong>YieldSage</strong> is a real-time yield aggregator and AI intelligence framework developed specifically for the <strong>Mantle Network</strong>. By monitoring decentralised liquidity, lending pools, and yield farms, YieldSage delivers automated risk assessments, optimal positioning models, and alerts straight to users.
              </p>
              <p>
                As DeFi ecosystems grow, yields become highly volatile. LPs and lenders are exposed to constant yield shifts, impermanent loss, and protocol solvency changes. YieldSage solves this by maintaining a background engine that indexes live pool metrics, ranks them using mathematical scoring functions, and broadcasts findings via an interactive assistant bot on Telegram and a web-based Pro dashboard.
              </p>
            </div>
            
            <div className="grid gap-6 grid-cols-1 md:grid-cols-3 pt-4">
              <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-[#00ff88]/10 flex items-center justify-center border border-[#00ff88]/20 text-[#00ff88]">
                  <Database className="w-4.5 h-4.5" />
                </div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-white/80">Real-Time Ingestion</h4>
                <p className="text-[11px] font-mono text-white/40 leading-relaxed">
                  Hourly data syncs with custom Dune dashboards tracking TVL, reward allocations, base rates, and token changes on-chain.
                </p>
              </div>
              
              <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 text-cyan-400">
                  <Cpu className="w-4.5 h-4.5" />
                </div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-white/80">Rotational Scorer</h4>
                <p className="text-[11px] font-mono text-white/40 leading-relaxed">
                  Rotational multi-LLM scoring framework classifies pools into Stable, Moderate, and Aggressive risk profiles.
                </p>
              </div>
              
              <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-400">
                  <Bot className="w-4.5 h-4.5" />
                </div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-white/80">Automated Bot alerts</h4>
                <p className="text-[11px] font-mono text-white/40 leading-relaxed">
                  Monitors user paper trade entries and pushes immediate recommendations if higher yields open within the same risk limits.
                </p>
              </div>
            </div>
          </section>

          {/* 2. Architecture Section */}
          <section id="architecture" className="space-y-6 scroll-mt-28">
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-[#00ff88] uppercase tracking-[0.2em]">02 / Architecture</span>
              <h2 className="text-3xl font-light tracking-tight font-sans">Core System Design</h2>
            </div>
            <p className="text-sm text-white/60 leading-relaxed font-sans max-w-3xl">
              YieldSage is split into three main components: a <strong>FastAPI Backend</strong> managing databases and cron triggers, a <strong>Next.js Web Client</strong> supplying the Pro Dashboard experience, and a <strong>Telegram Bot Handler</strong> running user communications.
            </p>
            
            <div className="p-6 bg-black/60 border border-white/5 rounded-2xl space-y-4">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-white/90 font-mono">System Flow & Data Topology</h4>
              
              {/* Responsive Visual Flowchart representing System Flow & Data Topology */}
              <div className="space-y-6">
                {/* Desktop View */}
                <div className="hidden md:flex flex-col items-center justify-center p-8 bg-white/[0.02] border border-white/5 rounded-xl space-y-6 font-mono text-xs">
                  {/* Row 1: Dune API */}
                  <div className="flex flex-col items-center">
                    <div className="px-5 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg shadow-[0_0_15px_rgba(16,185,129,0.05)]">
                      Dune API
                    </div>
                    <div className="w-[1px] h-6 bg-gradient-to-b from-emerald-500/50 to-cyan-500/50 flex items-center justify-center relative">
                      <div className="absolute top-full -translate-y-1 w-0 h-0 border-l-[3px] border-l-transparent border-r-[3px] border-r-transparent border-t-[5px] border-t-cyan-500/50" />
                    </div>
                    <span className="text-[10px] text-white/30 mt-1">Hourly fetch</span>
                  </div>

                  {/* Row 2: Dune Fetcher & Supabase */}
                  <div className="flex items-center gap-12">
                    <div className="px-5 py-2 bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 rounded-lg shadow-[0_0_15px_rgba(6,182,212,0.05)]">
                      Dune Fetcher
                    </div>
                    <div className="flex items-center">
                      <div className="h-[1px] w-12 bg-gradient-to-r from-cyan-500/50 to-blue-500/50 flex items-center justify-center relative">
                        <div className="absolute left-full -translate-x-1 w-0 h-0 border-t-[3px] border-t-transparent border-b-[3px] border-b-transparent border-l-[5px] border-l-blue-500/50" />
                      </div>
                    </div>
                    <div className="px-5 py-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg shadow-[0_0_15px_rgba(59,130,246,0.05)] flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                      Supabase Database
                    </div>
                  </div>

                  {/* Splitter Line from Supabase */}
                  <div className="flex flex-col items-center w-full relative h-8">
                    <div className="w-[1px] h-4 bg-blue-500/50 absolute top-0 left-1/2 -translate-x-1/2" />
                    <div className="w-[50%] h-[1px] bg-blue-500/30 absolute top-4 left-1/4" />
                    <div className="flex justify-between w-[50%] absolute top-4 left-1/4">
                      <div className="w-[1px] h-4 bg-blue-500/30" />
                      <div className="w-[1px] h-4 bg-blue-500/30" />
                    </div>
                  </div>

                  {/* Row 3: FastAPI App, AI Scorer, Telegram Bot */}
                  <div className="flex justify-between w-full items-start px-8">
                    {/* Left Column: API & Web */}
                    <div className="flex flex-col items-center w-5/12">
                      <div className="px-5 py-2 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-lg shadow-[0_0_15px_rgba(168,85,247,0.05)] text-center">
                        FastAPI App
                      </div>
                      <div className="w-[1px] h-8 bg-purple-500/50 flex items-center justify-center relative">
                        <div className="absolute top-full -translate-y-1 w-0 h-0 border-l-[3px] border-l-transparent border-r-[3px] border-r-transparent border-t-[5px] border-t-purple-500/50" />
                      </div>
                      <span className="text-[9px] text-white/30 mt-1 mb-1">REST API</span>
                      <div className="px-5 py-2 bg-[#00ff88]/10 border border-[#00ff88]/20 text-[#00ff88] rounded-lg shadow-[0_0_15px_rgba(0,255,136,0.05)] text-center">
                        Next.js Web (Pro Dash)
                      </div>
                    </div>

                    {/* Right Column: AI & Telegram */}
                    <div className="flex items-center justify-end w-7/12 gap-4 pt-2">
                      <div className="flex flex-col items-center">
                        <div className="px-5 py-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg shadow-[0_0_15px_rgba(245,158,11,0.05)] text-center">
                          AI Scorer
                        </div>
                        <span className="text-[9px] text-white/30 mt-1">Scoring / Recommendations</span>
                      </div>
                      <div className="flex items-center">
                        <div className="h-[1px] w-8 bg-gradient-to-r from-amber-500/50 to-pink-500/50 flex items-center justify-center relative">
                          <div className="absolute left-full -translate-x-1 w-0 h-0 border-t-[3px] border-t-transparent border-b-[3px] border-b-transparent border-l-[5px] border-l-pink-500/50" />
                        </div>
                      </div>
                      <div className="px-5 py-2 bg-pink-500/10 border border-pink-500/20 text-pink-400 rounded-lg shadow-[0_0_15px_rgba(236,72,153,0.05)] text-center">
                        Telegram Bot
                      </div>
                    </div>
                  </div>
                </div>

                {/* Mobile View */}
                <div className="flex md:hidden flex-col items-center gap-4 p-5 bg-white/[0.02] border border-white/5 rounded-xl font-mono text-[10px]">
                  <div className="px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg">Dune API</div>
                  <div className="text-white/20">↓ (Hourly fetch)</div>
                  <div className="px-3 py-1.5 bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 rounded-lg">Dune Fetcher</div>
                  <div className="text-white/20">↓</div>
                  <div className="px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                    Supabase Database
                  </div>
                  <div className="text-white/20">↓</div>
                  
                  <div className="w-full grid grid-cols-2 gap-3">
                    <div className="flex flex-col items-center p-3 bg-white/[0.01] border border-white/5 rounded-xl gap-2">
                      <span className="text-[8px] text-white/30 uppercase tracking-wider">Web Portal</span>
                      <div className="px-2 py-1 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded text-center">FastAPI App</div>
                      <div className="text-white/20">↓</div>
                      <div className="px-2 py-1 bg-[#00ff88]/10 border border-[#00ff88]/20 text-[#00ff88] rounded text-center">Next.js Web (Pro Dash)</div>
                    </div>
                    <div className="flex flex-col items-center p-3 bg-white/[0.01] border border-white/5 rounded-xl gap-2">
                      <span className="text-[8px] text-white/30 uppercase tracking-wider">AI Bot Channel</span>
                      <div className="px-2 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded text-center">AI Scorer</div>
                      <div className="text-white/20">↓</div>
                      <div className="px-2 py-1 bg-pink-500/10 border border-pink-500/20 text-pink-400 rounded text-center">Telegram Bot</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 3. Data Pipeline Section */}
          <section id="pipeline" className="space-y-6 scroll-mt-28">
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-[#00ff88] uppercase tracking-[0.2em]">03 / Ingestion Pipeline</span>
              <h2 className="text-3xl font-light tracking-tight font-sans">On-chain Data Pipeline</h2>
            </div>
            <div className="text-sm text-white/60 leading-relaxed font-sans space-y-4 max-w-3xl">
              <p>
                On-chain analytics are derived from custom Dune SQL queries compiling pool data on Mantle. The Python <code>DuneFetcher</code> service runs every hour to keep records synced.
              </p>
              <h3 className="text-sm font-semibold text-white/90 font-mono uppercase tracking-wide">Dune API Rotation & Key Security</h3>
              <p>
                To work around strict hourly query limits, the fetcher utilizes a rolling array of Dune API keys stored as a semicolon-separated string (<code>DUNE_API_KEYS</code>). Upon completing a query successfully, the engine automatically rolls the active index forward to avoid hitting rate-limiting caps.
              </p>
            </div>

            <div className="bg-white/[0.01] border border-white/5 rounded-2xl overflow-hidden relative group">
              <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 bg-black/60">
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest flex items-center gap-1.5">
                  <Code className="w-3.5 h-3.5 text-cyan-400" />
                  DuneFetcher key rotation snippet
                </span>
                <button
                  onClick={() => copyToClipboard(`def rotate_key(self):
    keys = [k.strip() for k in os.getenv("DUNE_API_KEYS", "").split(";") if k.strip()]
    if not keys: return
    self.key_index = (self.key_index + 1) % len(keys)
    logger.info(f"Rotated to Dune key index {self.key_index}")`, "key_rot")}
                  className="p-1 hover:bg-white/5 rounded text-white/40 hover:text-white transition-colors"
                >
                  {copiedText === "key_rot" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <pre className="p-5 text-[11px] font-mono text-white/70 overflow-x-auto bg-black/20">
{`def rotate_key(self):
    keys = [k.strip() for k in os.getenv("DUNE_API_KEYS", "").split(";") if k.strip()]
    if not keys: return
    self.key_index = (self.key_index + 1) % len(keys)
    logger.info(f"Rotated to Dune key index {self.key_index}")`}
              </pre>
            </div>
          </section>

          {/* 4. AI Scorer Section */}
          <section id="ai-scorer" className="space-y-6 scroll-mt-28">
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-[#00ff88] uppercase tracking-[0.2em]">04 / Cognitive Layer</span>
              <h2 className="text-3xl font-light tracking-tight font-sans">Rotational LLM Scorer</h2>
            </div>
            <div className="text-sm text-white/60 leading-relaxed font-sans space-y-4 max-w-3xl">
              <p>
                To provide institutional-grade yield advice, YieldSage scores protocols and individual pools using a dedicated LLM scoring engine. To guarantee 100% uptime and escape local provider limitations, the service implements a <strong>Rotational Provider Cascade</strong>.
              </p>
              <h3 className="text-sm font-semibold text-white/90 font-mono uppercase tracking-wide">The Model Cascade Chain</h3>
              <p>
                When generating hourly recommendations, the scoring pipeline rotates through API endpoints sequentially. If the primary provider times out, the engine catches the exception, logs it, and immediately forwards the payload to the next model in the chain:
              </p>
              <ol className="list-decimal pl-5 space-y-2 text-white/50 font-mono text-xs">
                <li><span className="text-[#00ff88]">Cerebras (Llama 3.1 70B)</span> — Maximum speed, primary pipeline</li>
                <li><span className="text-cyan-400">SambaNova (Llama 3.1 405B)</span> — Fallback 1 (high parameter capacity)</li>
                <li><span className="text-purple-400">Groq (Llama 3.3 70B)</span> — Fallback 2 (optimized latency)</li>
                <li><span className="text-rose-400">NVIDIA NIM (Llama 3 70B)</span> — Fallback 3 (reliable cloud compute)</li>
                <li><span className="text-blue-400">Google Gemini (Flash 1.5)</span> — Ultimate fallback (built-in fallback layer)</li>
              </ol>
            </div>
            
            <div className="bg-white/[0.01] border border-white/5 rounded-2xl overflow-hidden relative group">
              <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 bg-black/60">
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest flex items-center gap-1.5">
                  <Code className="w-3.5 h-3.5 text-cyan-400" />
                  Model Cascade Execution Loop
                </span>
                <button
                  onClick={() => copyToClipboard(`async def call_llm_cascade(self, prompt: str) -> str:
    providers = ["cerebras", "sambanova", "groq", "nvidia", "gemini"]
    for provider in providers:
        try:
            res = await self.call_provider(provider, prompt)
            if res: return res, provider
        except Exception as e:
            logger.warning(f"Provider {provider} failed: {e}. Cascading...")
    raise RuntimeError("All LLM providers failed.")`, "cascade_code")}
                  className="p-1 hover:bg-white/5 rounded text-white/40 hover:text-white transition-colors"
                >
                  {copiedText === "cascade_code" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <pre className="p-5 text-[11px] font-mono text-white/70 overflow-x-auto bg-black/20">
{`async def call_llm_cascade(self, prompt: str) -> str:
    providers = ["cerebras", "sambanova", "groq", "nvidia", "gemini"]
    for provider in providers:
        try:
            res = await self.call_provider(provider, prompt)
            if res: return res, provider
        except Exception as e:
            logger.warning(f"Provider {provider} failed: {e}. Cascading...")
    raise RuntimeError("All LLM providers failed.")`}
              </pre>
            </div>
          </section>

          {/* 5. Telegram Bot Section */}
          <section id="telegram" className="space-y-6 scroll-mt-28">
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-[#00ff88] uppercase tracking-[0.2em]">05 / User Interface</span>
              <h2 className="text-3xl font-light tracking-tight font-sans">Telegram Assistant</h2>
            </div>
            <div className="text-sm text-white/60 leading-relaxed font-sans space-y-4 max-w-3xl">
              <p>
                The primary conversational gateway is the official Telegram assistant bot (<code>t.me/YieldSageBot</code>). The bot processes commands, handles simulated paper trades, and monitors active user allocations.
              </p>
              <h3 className="text-sm font-semibold text-white/90 font-mono uppercase tracking-wide">Supported Commands</h3>
              <ul className="list-disc pl-5 space-y-2 text-white/50 font-mono text-xs">
                <li><code>/start</code> — Registers user, aligns default risk tiers, outputs interactive dashboard menu.</li>
                <li><code>/yields</code> — Displays dynamic paginated view of current yields.</li>
                <li><code>/trade</code> — Simulates paper-trading allocations inside Mantle pools.</li>
                <li><code>/positions</code> — Displays active paper-trading balances, entry APY, and current profit metrics.</li>
                <li><code>/alerts</code> — Toggles hourly background alert updates.</li>
                <li><code>/risk</code> — Modifies individual risk profile tags (Stable, Moderate, Aggressive).</li>
              </ul>
            </div>
          </section>

          {/* 6. API Reference Section */}
          <section id="api-ref" className="space-y-6 scroll-mt-28">
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-[#00ff88] uppercase tracking-[0.2em]">06 / Integrations</span>
              <h2 className="text-3xl font-light tracking-tight font-sans">API Specifications</h2>
            </div>
            <p className="text-sm text-white/60 leading-relaxed font-sans max-w-3xl">
              The FastAPI backend exposes several public REST endpoints for the Pro Dashboard. The base URL is automatically resolved based on local/production deployment.
            </p>

            <div className="space-y-6">
              {/* Endpoint 1 */}
              <div className="bg-white/[0.02] border border-white/5 rounded-2xl overflow-hidden">
                <div className="px-5 py-3 border-b border-white/5 bg-black/60 flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-[#00ff88] text-[10px] font-bold font-mono">GET</span>
                    <span className="text-xs font-mono font-semibold">/api/yields/leaderboard</span>
                  </div>
                  <span className="text-[10px] font-mono text-white/30">Yield opportunities query</span>
                </div>
                <div className="p-5 space-y-3">
                  <p className="text-xs text-white/50 leading-relaxed">Returns paginated lists of pools, with filter controls for APY, TVL, and risk tier.</p>
                  <table className="w-full text-left text-[11px] font-mono border-collapse divide-y divide-white/5">
                    <thead>
                      <tr className="text-white/40">
                        <th className="py-2">Query Param</th>
                        <th className="py-2">Type</th>
                        <th className="py-2">Description</th>
                      </tr>
                    </thead>
                    <tbody className="text-white/60 divide-y divide-white/5">
                      <tr><td className="py-2"><code>page</code></td><td>integer</td><td>Page index (default: 1)</td></tr>
                      <tr><td className="py-2"><code>pageSize</code></td><td>integer</td><td>Items per page (default: 20)</td></tr>
                      <tr><td className="py-2"><code>search</code></td><td>string</td><td>Filter by protocol name or asset</td></tr>
                      <tr><td className="py-2"><code>min_tvl</code></td><td>number</td><td>Minimum pool TVL</td></tr>
                      <tr><td className="py-2"><code>min_apy</code></td><td>number</td><td>Minimum pool APY</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Endpoint 2 */}
              <div className="bg-white/[0.02] border border-white/5 rounded-2xl overflow-hidden">
                <div className="px-5 py-3 border-b border-white/5 bg-black/60 flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-[#00ff88] text-[10px] font-bold font-mono">GET</span>
                    <span className="text-xs font-mono font-semibold">/api/stats/overview</span>
                  </div>
                  <span className="text-[10px] font-mono text-white/30">Overview stats</span>
                </div>
                <div className="p-5 space-y-3">
                  <p className="text-xs text-white/50 leading-relaxed">Headline numbers for the dashboard cards, such as TVL, average APY, unique protocols, and pool count.</p>
                  <div className="bg-black/40 border border-white/5 p-4 rounded-xl">
                    <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">Example Response</p>
                    <pre className="text-[10px] font-mono text-cyan-400 overflow-x-auto leading-relaxed">
{`{
  "protocols_tracked": 12,
  "pools_tracked": 152,
  "total_tvl": 45678239.12,
  "average_apy": 14.28,
  "median_apy": 8.52,
  "last_data_refresh": "2026-06-02T20:00:00.000Z"
}`}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 7. FAQ Section */}
          <section id="faq" className="space-y-6 scroll-mt-28">
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-[#00ff88] uppercase tracking-[0.2em]">07 / FAQ</span>
              <h2 className="text-3xl font-light tracking-tight font-sans">Frequently Asked Questions</h2>
            </div>
            
            <div className="space-y-4 max-w-3xl">
              <div className="bg-white/[0.01] border border-white/5 rounded-2xl p-5 space-y-2">
                <h4 className="text-xs font-semibold text-[#00ff88] uppercase font-mono">Why does the dashboard protocol count differ from total rows?</h4>
                <p className="text-xs text-white/50 leading-relaxed font-sans">
                  The dashboard counts unique protocol names (e.g. merchant-moe, aave-v3) rather than counting every individual pool address as a distinct protocol. This provides an accurate picture of platform diversity.
                </p>
              </div>

              <div className="bg-white/[0.01] border border-white/5 rounded-2xl p-5 space-y-2">
                <h4 className="text-xs font-semibold text-[#00ff88] uppercase font-mono">Why do TVL values not match DefiLlama exactly?</h4>
                <p className="text-xs text-white/50 leading-relaxed font-sans">
                  YieldSage monitors high-liquidity active yield opportunities to ensure the safety and efficiency of recommendation models. Low-liquidity pools or inactive pools are filtered out, which can result in minor TVL variations compared to aggregate indexes.
                </p>
              </div>

              <div className="bg-white/[0.01] border border-white/5 rounded-2xl p-5 space-y-2">
                <h4 className="text-xs font-semibold text-[#00ff88] uppercase font-mono">How does the Telegram bot verify on-chain recommendations?</h4>
                <p className="text-xs text-white/50 leading-relaxed font-sans">
                  Every recommendation generated by the model cascade includes an on-chain transaction hash verifying the data state. Users can click the transaction link to review the proofs on the Mantlescan explorer directly.
                </p>
              </div>
            </div>
          </section>

        </div>

      </div>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-black/40 py-8 relative z-10">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-12 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-[10px] font-mono text-white/20">
            YieldSage Documentation Engine v1.0.0
          </span>
          <div className="flex items-center gap-4 text-xs font-mono text-white/40">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <span>·</span>
            <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
          </div>
        </div>
      </footer>

      {/* Hide Scrollbar styling */}
      <style dangerouslySetInnerHTML={{ __html: `
        .no-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .no-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .mask-fade-edges {
          mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
          -webkit-mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
        }
      `}} />
    </div>
  );
}
