"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export function LeaderboardTable() {
  const [riskFilter, setRiskFilter] = useState<string>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["leaderboard", riskFilter],
    queryFn: () => api.getLeaderboard(50, 0, riskFilter),
    refetchInterval: 60000,
  });

  const riskColors: Record<string, string> = {
    stable: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    moderate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    aggressive: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  return (
    <Card className="bg-[#0A0A0A] border-white/5">
      <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 space-y-4 sm:space-y-0">
        <CardTitle className="text-xl font-medium text-white">Live Yield Leaderboard</CardTitle>
        <div className="flex bg-black p-1 rounded-md border border-white/5">
          {["all", "stable", "moderate", "aggressive"].map((filter) => (
            <button
              key={filter}
              onClick={() => setRiskFilter(filter)}
              className={`px-4 py-1.5 text-xs font-medium rounded capitalize transition-all ${
                riskFilter === filter
                  ? "bg-white/10 text-white"
                  : "text-white/40 hover:text-white/70"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-white/40 uppercase bg-black/40 border-y border-white/5">
              <tr>
                <th className="px-6 py-4 font-medium">Protocol</th>
                <th className="px-6 py-4 font-medium">Asset</th>
                <th className="px-6 py-4 font-medium">Risk</th>
                <th className="px-6 py-4 font-medium text-right">TVL</th>
                <th className="px-6 py-4 font-medium text-right">Current APY</th>
                <th className="px-6 py-4 font-medium text-right">7d Avg</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-white/40">
                    Loading yields...
                  </td>
                </tr>
              ) : data?.data?.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-white/40">
                    No pools found for this filter.
                  </td>
                </tr>
              ) : (
                data?.data?.map((row: any) => {
                  const protocol = row.protocol || {};
                  
                  // Compare current APY with 7d average
                  const apyDiff = row.apy - (row.apy_7d || row.apy);
                  const isUp = apyDiff > 0.1;
                  const isDown = apyDiff < -0.1;

                  return (
                    <tr key={row.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-white">{protocol.name}</div>
                        <div className="text-xs text-white/50">{protocol.pool_name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-white font-medium">{row.asset}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium uppercase border ${riskColors[protocol.risk_tag] || "bg-white/10 text-white/70"}`}>
                          {protocol.risk_tag}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="text-white/70">
                          {row.tvl_usd ? `$${(row.tvl_usd / 1000000).toFixed(2)}M` : "N/A"}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="text-lg font-bold text-emerald-400">
                          {row.apy?.toFixed(2)}%
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-white/50">
                        <div className="flex items-center justify-end gap-1">
                          {row.apy_7d?.toFixed(2)}%
                          {isUp ? (
                            <TrendingUp className="h-3 w-3 text-emerald-500" />
                          ) : isDown ? (
                            <TrendingDown className="h-3 w-3 text-red-500" />
                          ) : (
                            <Minus className="h-3 w-3 text-white/30" />
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
