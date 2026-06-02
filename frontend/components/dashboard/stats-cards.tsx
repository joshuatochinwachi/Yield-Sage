"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, LayoutGrid, Zap } from "lucide-react";

export function StatsCards() {
  const { data, isLoading } = useQuery({
    queryKey: ["overviewStats"],
    queryFn: api.getOverviewStats,
    refetchInterval: 60000,
  });

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="bg-[#0A0A0A] border-white/5">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-white/50">
            Active Protocols
          </CardTitle>
          <LayoutGrid className="h-4 w-4 text-emerald-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-white">
            {isLoading ? "..." : data?.protocols_tracked || 0}
          </div>
          <p className="text-xs text-white/40 mt-1">Tracked on Mantle</p>
        </CardContent>
      </Card>

      <Card className="bg-[#0A0A0A] border-white/5">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-white/50">
            Highest Yield
          </CardTitle>
          <Zap className="h-4 w-4 text-amber-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-white">
            {isLoading ? "..." : `${(data?.best_apy || 0).toFixed(2)}%`}
          </div>
          <p className="text-xs text-white/40 mt-1">Across all risk tiers</p>
        </CardContent>
      </Card>

      <Card className="bg-[#0A0A0A] border-white/5">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-white/50">
            AI Recommendations
          </CardTitle>
          <Activity className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-white">
            {isLoading ? "..." : data?.recommendations_generated || 0}
          </div>
          <p className="text-xs text-white/40 mt-1">
            {data?.on_chain_proofs || 0} backed by on-chain proofs
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
