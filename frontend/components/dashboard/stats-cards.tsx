"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Database, Coins, Flame, Percent, Cpu, Info } from "lucide-react";
import { useState } from "react";

function formatTVL(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export function StatsCards() {
  const { data, isLoading } = useQuery({
    queryKey: ["overviewStats"],
    queryFn: api.getOverviewStats,
    refetchInterval: 60000,
  });

  return (
    <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
      {/* Total DeFi TVL */}
      <Card className="bg-black/40 backdrop-blur-xl border-white/5 hover:bg-white/[0.04] hover:-translate-y-0.5 transition-all duration-300 relative group">
        <div className="absolute inset-0 bg-emerald-500/0 group-hover:bg-[#00ff88]/5 transition-colors duration-500 rounded-xl" />
        <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
          <div className="flex items-center gap-1.5 relative group/tooltip">
            <CardTitle className="text-[10px] font-semibold font-mono tracking-wider text-white/40 uppercase cursor-help">
              DeFi TVL
            </CardTitle>
            <Info className="h-3 w-3 text-white/30 hover:text-white/60 cursor-help transition-colors" />
            <div className="absolute bottom-full left-0 mb-2 w-56 p-2.5 bg-black/95 border border-white/10 rounded-xl text-[9px] text-white/70 font-mono leading-relaxed opacity-0 invisible group-hover/tooltip:opacity-100 group-hover/tooltip:visible transition-all duration-200 z-50 shadow-2xl pointer-events-none">
              This TVL represents the coverage of protocols integrated with YieldSage. It may not exactly match DeFiLlama's total ecosystem TVL due to data coverage filtering.
            </div>
          </div>
          <Coins className="h-4 w-4 text-[#00ff88] group-hover:drop-shadow-[0_0_8px_rgba(0,255,136,0.8)] transition-all" />
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="text-xl md:text-2xl font-bold font-mono text-white tracking-tight">
            {isLoading ? (
              <span className="inline-block w-16 h-6 bg-white/5 animate-pulse rounded" />
            ) : (
              formatTVL(data?.total_tvl)
            )}
          </div>
          <p className="text-[10px] text-white/40 font-mono mt-1">Mantle Ecosystem</p>
        </CardContent>
      </Card>

      {/* Average APY */}
      <Card className="bg-black/40 backdrop-blur-xl border-white/5 hover:bg-white/[0.04] hover:-translate-y-0.5 transition-all duration-300 relative overflow-hidden group">
        <div className="absolute inset-0 bg-amber-500/0 group-hover:bg-amber-500/5 transition-colors duration-500" />
        <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
          <CardTitle className="text-[10px] font-semibold font-mono tracking-wider text-white/40 uppercase">
            Average APY
          </CardTitle>
          <Percent className="h-4 w-4 text-amber-400 group-hover:drop-shadow-[0_0_8px_rgba(245,158,11,0.8)] transition-all" />
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="text-xl md:text-2xl font-bold font-mono text-amber-400 tracking-tight">
            {isLoading ? (
              <span className="inline-block w-16 h-6 bg-white/5 animate-pulse rounded" />
            ) : (
              `${(data?.average_apy || 0).toFixed(2)}%`
            )}
          </div>
          <p className="text-[10px] text-white/40 font-mono mt-1">Arithmetic Mean</p>
        </CardContent>
      </Card>

      {/* Median APY */}
      <Card className="bg-black/40 backdrop-blur-xl border-white/5 hover:bg-white/[0.04] hover:-translate-y-0.5 transition-all duration-300 relative overflow-hidden group">
        <div className="absolute inset-0 bg-purple-500/0 group-hover:bg-purple-500/5 transition-colors duration-500" />
        <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
          <CardTitle className="text-[10px] font-semibold font-mono tracking-wider text-white/40 uppercase">
            Median APY
          </CardTitle>
          <Flame className="h-4 w-4 text-purple-400 group-hover:drop-shadow-[0_0_8px_rgba(168,85,247,0.8)] transition-all" />
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="text-xl md:text-2xl font-bold font-mono text-purple-400 tracking-tight">
            {isLoading ? (
              <span className="inline-block w-16 h-6 bg-white/5 animate-pulse rounded" />
            ) : (
              `${(data?.median_apy || 0).toFixed(2)}%`
            )}
          </div>
          <p className="text-[10px] text-white/40 font-mono mt-1">Mid-point yield</p>
        </CardContent>
      </Card>

      {/* Protocols count */}
      <Card className="bg-black/40 backdrop-blur-xl border-white/5 hover:bg-white/[0.04] hover:-translate-y-0.5 transition-all duration-300 relative overflow-hidden group">
        <div className="absolute inset-0 bg-cyan-500/0 group-hover:bg-cyan-500/5 transition-colors duration-500" />
        <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
          <CardTitle className="text-[10px] font-semibold font-mono tracking-wider text-white/40 uppercase">
            Protocols
          </CardTitle>
          <Cpu className="h-4 w-4 text-cyan-400 group-hover:drop-shadow-[0_0_8px_rgba(34,211,238,0.8)] transition-all" />
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="text-xl md:text-2xl font-bold font-mono text-cyan-400 tracking-tight">
            {isLoading ? (
              <span className="inline-block w-12 h-6 bg-white/5 animate-pulse rounded" />
            ) : (
              data?.protocols_tracked || 0
            )}
          </div>
          <p className="text-[10px] text-white/40 font-mono mt-1">Active protocols</p>
        </CardContent>
      </Card>

      {/* Pools count */}
      <Card className="bg-black/40 backdrop-blur-xl border-white/5 hover:bg-white/[0.04] hover:-translate-y-0.5 transition-all duration-300 relative overflow-hidden group col-span-2 lg:col-span-1">
        <div className="absolute inset-0 bg-pink-500/0 group-hover:bg-pink-500/5 transition-colors duration-500" />
        <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
          <CardTitle className="text-[10px] font-semibold font-mono tracking-wider text-white/40 uppercase">
            Active Pools
          </CardTitle>
          <Database className="h-4 w-4 text-pink-400 group-hover:drop-shadow-[0_0_8px_rgba(244,114,182,0.8)] transition-all" />
        </CardHeader>
        <CardContent className="relative z-10">
          <div className="text-xl md:text-2xl font-bold font-mono text-pink-400 tracking-tight">
            {isLoading ? (
              <span className="inline-block w-12 h-6 bg-white/5 animate-pulse rounded" />
            ) : (
              data?.pools_tracked || 0
            )}
          </div>
          <p className="text-[10px] text-white/40 font-mono mt-1">Monitored pools</p>
        </CardContent>
      </Card>
    </div>
  );
}
