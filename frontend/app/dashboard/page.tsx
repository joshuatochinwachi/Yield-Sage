"use client";

import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecommendationCard } from "@/components/dashboard/recommendation-card";
import { LeaderboardTable } from "@/components/dashboard/leaderboard-table";

export default function DashboardPage() {
  return (
    <div className="min-h-screen pt-24 pb-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight font-serif">
          Yield Intelligence
        </h1>
        <p className="text-white/50 mt-1">
          Real-time APY tracking, AI-driven recommendations, and risk-adjusted metrics for Mantle.
        </p>
      </div>

      {/* Top Section: Recommendation (left) and Stats (right) */}
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <RecommendationCard />
        </div>
        <div className="lg:col-span-2">
          <StatsCards />
        </div>
      </div>

      {/* Main Section: Leaderboard */}
      <div>
        <LeaderboardTable />
      </div>
    </div>
  );
}
