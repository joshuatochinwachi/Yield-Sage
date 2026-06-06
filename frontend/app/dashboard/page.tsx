"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecommendationCard } from "@/components/dashboard/recommendation-card";
import { LeaderboardTable } from "@/components/dashboard/leaderboard-table";
import { ProtocolCharts } from "@/components/dashboard/protocol-charts";
import { FloatingAIBubble } from "@/components/dashboard/floating-ai-bubble";
import { MouseGradientBackground } from "@/components/mouse-gradient-background";
import { WatchlistProvider } from "@/components/dashboard/watchlist-provider";
import { StorageConsent } from "@/components/storage-consent";
import Link from "next/link";
import { Send, BrainCircuit, BarChart3 } from "lucide-react";
import { useState } from "react";

type InsightTab = "ai" | "charts";

export default function DashboardPage() {
  const [insightTab, setInsightTab] = useState<InsightTab>("ai");

  // Fetch full leaderboard data for the summary charts
  const { data: fullLeaderboard, isLoading: isChartsLoading } = useQuery({
    queryKey: ["fullLeaderboardForCharts"],
    queryFn: () => api.getLeaderboard({ page: 1, pageSize: 500 }),
    refetchInterval: 60000,
  });

  return (
    <WatchlistProvider>
      <div className="min-h-screen relative overflow-hidden bg-[#050505] text-white">
        {/* Interactive mouse background spotlight and noise grain */}
        <MouseGradientBackground />
        
        {/* Local storage / cookie consent banner */}
        <StorageConsent />

        {/* Dancing/Floating AI Bot Bubble */}
        <FloatingAIBubble />

        {/* Sticky Glassmorphic Navbar */}
        <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-black/40 backdrop-blur-xl transition-all duration-300">
          <div className="flex h-16 w-full max-w-[1600px] mx-auto items-center justify-between px-4 sm:px-6 lg:px-12 xl:px-16">
            <div className="flex items-center gap-6">
              {/* Clickable Logo and Brand Name */}
              <Link href="/" className="flex items-center gap-2.5 group">
                <img 
                  src="/logo.jpg" 
                  alt="YieldSage Logo" 
                  className="w-8 h-8 rounded-lg border border-white/10 group-hover:border-[#00ff88]/50 object-cover transition-colors duration-300"
                />
                <span className="font-sans font-light tracking-wider text-sm text-white/90 group-hover:text-white transition-colors duration-300">
                  YIELD<span className="text-[#00ff88] font-medium font-mono">SAGE</span>
                </span>
              </Link>
              
              {/* Nav links */}
              <nav className="hidden md:flex items-center gap-6 text-xs font-mono text-white/40 uppercase tracking-widest pt-0.5">
                <Link href="/" className="hover:text-white transition-colors">Home</Link>
                <Link href="/dashboard" className="text-[#00ff88] hover:text-white transition-colors">Dashboard</Link>
                <Link href="/docs" className="hover:text-white transition-colors">Docs</Link>
              </nav>
            </div>

            {/* Right side bot callout */}
            <div className="flex items-center gap-4">
              <a 
                href="https://t.me/YieldSageBot"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-[#00ff88]/10 hover:bg-[#00ff88]/20 text-[#00ff88] border border-[#00ff88]/30 shadow-[0_0_15px_rgba(0,255,136,0.05)] transition-all duration-300"
              >
                Launch YieldSage AI Agent
                <Send className="h-3 w-3" />
              </a>
            </div>
          </div>
        </header>

        {/* Main Content Body */}
        <main className="relative z-10 w-full max-w-[1600px] mx-auto pt-10 pb-20 px-4 sm:px-6 lg:px-12 xl:px-16 space-y-8 animate-in fade-in duration-700">
          <div className="space-y-1">
            <h1 className="text-4xl sm:text-5xl font-light text-white tracking-tight font-sans">
              Yield Intelligence
            </h1>
            <p className="text-white/60 text-xs sm:text-sm font-light max-w-2xl font-mono leading-relaxed">
              Real-time APY tracking, AI-driven recommendations, and risk-adjusted metrics for the Mantle network.
            </p>
          </div>

          {/* Stats Cards Section */}
          <StatsCards />

          {/* AI Agent Features Banner */}
          <div className="relative overflow-hidden rounded-2xl border border-[#00ff88]/20 bg-[#00ff88]/[0.02] p-6 sm:p-8">
            <div className="absolute inset-0 bg-gradient-to-r from-[#00ff88]/10 via-transparent to-transparent pointer-events-none" />
            <div className="relative flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
              <div className="flex-1 space-y-2.5">
                <div className="flex items-center gap-2 text-[#00ff88] font-mono text-xs font-semibold tracking-wider uppercase">
                  <BrainCircuit className="w-4 h-4" />
                  <span>YieldSage Telegram Agent</span>
                </div>
                <h3 className="text-xl sm:text-2xl font-light text-white font-sans tracking-tight">
                  Simulate trades directly or chat with the AI Agent.
                </h3>
                <p className="text-white/60 text-sm max-w-3xl font-mono leading-relaxed">
                  Click <span className="text-white font-semibold">Simulate</span> on any yield pool to run a paper trade instantly, or chat with the agent for personalized portfolio analysis, risk profiling, and hourly updates.
                </p>
              </div>
              <div className="flex-shrink-0 w-full lg:w-auto">
                <a
                  href="https://t.me/YieldSageBot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-[#00ff88]/10 hover:bg-[#00ff88]/20 text-[#00ff88] border border-[#00ff88]/30 shadow-[0_0_20px_rgba(0,255,136,0.1)] transition-all duration-300 font-mono text-xs uppercase tracking-wider font-semibold group w-full lg:w-auto"
                >
                  <Send className="w-4 h-4 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 transition-transform" />
                  Chat With Agent
                </a>
              </div>
            </div>
          </div>

          {/* Full-Width Leaderboard Table */}
          <LeaderboardTable />

          {/* Insight Panel — tabbed section below the table */}
          <div className="rounded-2xl border border-white/5 bg-black/30 backdrop-blur-xl overflow-hidden shadow-2xl">
            {/* Tab header */}
            <div className="flex items-center gap-0 border-b border-white/5 px-2 pt-2">
              <button
                onClick={() => setInsightTab("ai")}
                className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold font-mono uppercase tracking-widest rounded-t-xl border-b-2 transition-all duration-200 ${
                  insightTab === "ai"
                    ? "text-[#00ff88] border-[#00ff88] bg-[#00ff88]/5"
                    : "text-white/30 border-transparent hover:text-white/60"
                }`}
              >
                <BrainCircuit className="h-3.5 w-3.5" />
                AI Picks
              </button>
              <button
                onClick={() => setInsightTab("charts")}
                className={`flex items-center gap-2 px-5 py-3 text-xs font-semibold font-mono uppercase tracking-widest rounded-t-xl border-b-2 transition-all duration-200 ${
                  insightTab === "charts"
                    ? "text-[#00ff88] border-[#00ff88] bg-[#00ff88]/5"
                    : "text-white/30 border-transparent hover:text-white/60"
                }`}
              >
                <BarChart3 className="h-3.5 w-3.5" />
                TVL Distribution
              </button>
            </div>

            {/* Tab body */}
            <div className="p-6">
              {insightTab === "ai" && (
                <div className="animate-in fade-in duration-300">
                  <RecommendationCard />
                </div>
              )}
              {insightTab === "charts" && (
                <div className="animate-in fade-in duration-300">
                  <ProtocolCharts data={fullLeaderboard?.data} isLoading={isChartsLoading} />
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </WatchlistProvider>
  );
}
