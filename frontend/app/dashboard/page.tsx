"use client";

import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecommendationCard } from "@/components/dashboard/recommendation-card";
import { LeaderboardTable } from "@/components/dashboard/leaderboard-table";
import { MouseGradientBackground } from "@/components/mouse-gradient-background";
import { WatchlistProvider } from "@/components/dashboard/watchlist-provider";
import { StorageConsent } from "@/components/storage-consent";

export default function DashboardPage() {
  return (
    <WatchlistProvider>
      <div className="min-h-screen relative overflow-hidden bg-[#050505]">
        {/* Interactive mouse background spotlight and noise grain */}
        <MouseGradientBackground />
        
        {/* Local storage / cookie consent banner */}
        <StorageConsent />

        <div className="relative z-10 pt-24 pb-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-700">
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

          {/* Main Grid: AI Recommendation Pick (left/1-col) and Live Leaderboard Table (right/2-col) */}
          <div className="grid gap-8 grid-cols-1 xl:grid-cols-3">
            <div className="xl:col-span-1">
              <RecommendationCard />
            </div>
            <div className="xl:col-span-2">
              <LeaderboardTable />
            </div>
          </div>
        </div>
      </div>
    </WatchlistProvider>
  );
}
