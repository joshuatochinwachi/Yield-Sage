"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BrainCircuit, ExternalLink } from "lucide-react";

export function RecommendationCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["latestRecommendations"],
    queryFn: api.getLatestRecommendations,
    refetchInterval: 60000,
  });

  const bestRec = data?.[0]; // Usually highest ranked

  return (
    <Card className="bg-gradient-to-br from-emerald-950/20 to-black border-emerald-900/30 overflow-hidden relative">
      {/* Glow effect */}
      <div className="absolute -top-24 -right-24 w-48 h-48 bg-emerald-500/10 blur-3xl rounded-full pointer-events-none" />

      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div className="space-y-1">
          <CardTitle className="text-sm font-medium text-emerald-400 flex items-center gap-2">
            <BrainCircuit className="h-4 w-4" />
            Top AI Pick
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-24 flex items-center justify-center text-white/40">Loading recommendation...</div>
        ) : !bestRec ? (
          <div className="h-24 flex items-center justify-center text-white/40">No recommendations available</div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-end justify-between">
              <div>
                <h3 className="text-xl font-bold text-white mb-1">
                  {bestRec.protocol.name}
                </h3>
                <p className="text-sm text-white/50">{bestRec.protocol.pool_name}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-emerald-400">
                  {bestRec.apy_at_time.toFixed(2)}% APY
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 mt-1 uppercase border border-emerald-500/20">
                  {bestRec.risk_tag} Risk
                </span>
              </div>
            </div>
            
            <div className="bg-black/40 rounded p-3 text-sm text-white/70 border border-white/5 leading-relaxed">
              <span className="text-emerald-500/70 font-mono text-xs mr-2">{"//"}</span>
              {bestRec.ai_reasoning}
            </div>

            {bestRec.on_chain_tx_hash && (
              <div className="pt-2 flex justify-end">
                <a 
                  href={`https://explorer.mantle.xyz/tx/${bestRec.on_chain_tx_hash}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-white/40 hover:text-emerald-400 flex items-center gap-1 transition-colors"
                >
                  View On-Chain Proof <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
