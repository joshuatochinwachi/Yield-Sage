"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BrainCircuit, ExternalLink, ArrowRight, ShieldCheck, Sparkles, Send } from "lucide-react";
import { useState, useMemo } from "react";

// Helper to format timestamps nicely as "X ago"
function formatTimeAgo(dateString?: string): string {
  if (!dateString) return "Recently";
  try {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ${minutes % 60}m ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } catch (e) {
    return "Recently";
  }
}

export function RecommendationCard() {
  const [selectedRisk, setSelectedRisk] = useState<"stable" | "moderate" | "aggressive">("stable");

  const { data, isLoading } = useQuery({
    queryKey: ["latestRecommendations"],
    queryFn: api.getLatestRecommendations,
    refetchInterval: 60000,
  });

  // Extract picks from the response object
  const picks = useMemo(() => {
    return data?.data || {};
  }, [data]);

  const hasPicks = useMemo(() => {
    return Object.values(picks).some(p => p !== null && p !== undefined);
  }, [picks]);

  const activePick = picks[selectedRisk];

  // Helper colors for different risk tiers
  const tierConfig = {
    stable: {
      color: "text-blue-400",
      glow: "bg-blue-500/10",
      borderColor: "border-blue-500/20",
      glowBorder: "via-blue-500/50",
      bgHover: "group-hover:bg-blue-500/5",
      badge: "bg-blue-500/10 text-blue-400 border-blue-500/20"
    },
    moderate: {
      color: "text-amber-400",
      glow: "bg-amber-500/10",
      borderColor: "border-amber-500/20",
      glowBorder: "via-amber-500/50",
      bgHover: "group-hover:bg-amber-500/5",
      badge: "bg-amber-500/10 text-amber-400 border-amber-500/20"
    },
    aggressive: {
      color: "text-red-400",
      glow: "bg-red-500/10",
      borderColor: "border-red-500/20",
      glowBorder: "via-red-500/50",
      bgHover: "group-hover:bg-red-500/5",
      badge: "bg-red-500/10 text-red-400 border-red-500/20"
    }
  };

  const currentTheme = tierConfig[selectedRisk];

  return (
    <Card className={`bg-black/40 backdrop-blur-xl border-white/5 overflow-hidden relative group transition-all duration-500`}>
      {/* Background glow linked to active risk selection */}
      <div className={`absolute -top-24 -right-24 w-48 h-48 ${currentTheme.glow} blur-[80px] rounded-full pointer-events-none transition-colors duration-700`} />
      <div className={`absolute inset-0 bg-transparent ${currentTheme.bgHover} transition-colors duration-500`} />

      <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 relative z-10 border-b border-white/5 space-y-3 sm:space-y-0">
        <div className="space-y-0.5">
          <CardTitle className="text-sm font-semibold text-white/90 flex items-center gap-2 tracking-wider uppercase font-sans">
            <BrainCircuit className="h-4.5 w-4.5 text-[#00ff88] drop-shadow-[0_0_8px_rgba(0,255,136,0.5)]" />
            YieldSage AI recommendations
            <span className="relative flex h-1.5 w-1.5 ml-1">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00ff88] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#00ff88]"></span>
            </span>
          </CardTitle>
        </div>

        {/* Risk Selection Tabs */}
        {hasPicks && (
          <div className="flex bg-white/5 p-1 rounded-xl border border-white/10">
            {(["stable", "moderate", "aggressive"] as const).map((risk) => (
              <button
                key={risk}
                onClick={() => setSelectedRisk(risk)}
                className={`px-3 py-1 text-[10px] font-semibold rounded-lg capitalize transition-all duration-300 ${
                  selectedRisk === risk
                    ? "bg-white/10 text-white shadow-sm border border-white/5"
                    : "text-white/40 hover:text-white/70"
                }`}
              >
                {risk}
              </button>
            ))}
          </div>
        )}
      </CardHeader>
      
      <CardContent className="relative z-10 pt-5">
        {isLoading ? (
          <div className="h-32 flex flex-col items-center justify-center text-white/40 font-mono text-xs animate-pulse space-y-2">
            <Sparkles className="h-5 w-5 text-[#00ff88] animate-spin" />
            <span>Scanning yields and computing models...</span>
          </div>
        ) : (!hasPicks || !activePick) ? (
          /* Telegram fallback if no AI picks exist in database */
          <div className="space-y-4 py-2">
            <div className="text-center space-y-2 max-w-[480px] mx-auto">
              <div className="inline-flex p-3 bg-white/5 rounded-full border border-white/10 text-white/40 mb-1">
                <Send className="h-5 w-5 text-[#00ff88] drop-shadow-[0_0_8px_rgba(0,255,136,0.3)] animate-pulse" />
              </div>
              <h4 className="text-sm font-medium text-white">AI Recommendations refresh hourly</h4>
              <p className="text-xs text-white/50 leading-relaxed font-mono">
                Open live paper trades, request custom risk matrices, and receive instant alert notifications directly via our official Telegram assistant bot.
              </p>
            </div>
            
            <div className="pt-2 flex justify-center">
              <a 
                href="https://t.me/YieldSageBot" 
                target="_blank" 
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-5 py-2 text-xs font-semibold rounded-lg bg-[#00ff88] hover:bg-[#00ff88]/90 text-black shadow-[0_0_20px_rgba(0,255,136,0.15)] transition-all duration-300 hover:-translate-y-0.5"
              >
                Launch YieldSage AI Agent
                <ArrowRight className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        ) : (
          /* Render Active Pick */
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-semibold border ${currentTheme.badge} uppercase font-mono`}>
                    {activePick.risk_tag} Risk
                  </span>
                  <span className="text-[10px] text-white/30 font-mono">
                    Updated {formatTimeAgo(activePick.created_at)}
                  </span>
                </div>
                <h3 className="text-xl font-light text-white tracking-tight flex items-center gap-1.5 pt-1">
                  {activePick.protocols?.name || "Unknown"}
                  {activePick.protocols?.pool_name && (
                    <span className="text-white/40 text-xs font-mono">({activePick.protocols.pool_name})</span>
                  )}
                </h3>
                <p className="text-xs text-white/40 font-mono">
                  Asset: <span className="text-white/70 font-semibold">{activePick.protocols?.pool_name || "Mantle Pool"}</span>
                </p>
              </div>
              
              <div className="text-left sm:text-right flex sm:flex-col justify-between sm:justify-start items-center sm:items-end">
                <div className="text-2xl font-bold text-[#00ff88] font-mono drop-shadow-[0_0_8px_rgba(0,255,136,0.4)]">
                  {activePick.apy_at_time !== null ? `${activePick.apy_at_time.toFixed(2)}% APY` : "N/A"}
                </div>
                {activePick.ai_model && (
                  <span className="inline-flex items-center gap-1 text-[9px] text-white/30 font-mono mt-1" title="Model provider logs">
                    <ShieldCheck className="h-3 w-3 text-emerald-500" />
                    {activePick.ai_model.split("/").pop()}
                  </span>
                )}
              </div>
            </div>
            
            {/* Reasoning text block */}
            <div className={`bg-black/60 rounded-xl p-4 text-xs text-white/70 border ${currentTheme.borderColor} leading-relaxed font-mono relative overflow-hidden group-hover:border-emerald-500/20 transition-all duration-300`}>
              <div className={`absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent ${currentTheme.glowBorder} to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
              <span className="text-[#00ff88] mr-2">{"//"} Reasoning:</span>
              {activePick.ai_reasoning}
            </div>

            {/* Actions: Invest and On-chain Verification Links */}
            <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-white/5">
              <div>
                {activePick.on_chain_tx_hash ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <a 
                      href={`https://mantlescan.xyz/tx/${activePick.on_chain_tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs font-mono text-[#4ADE80] hover:underline underline-offset-2 transition-opacity hover:opacity-80"
                    >
                      <span>⛓</span>
                      <span>Verify on Mantle</span>
                      <span className="text-[#52504D]">{activePick.on_chain_tx_hash.slice(0, 8)}...{activePick.on_chain_tx_hash.slice(-6)}</span>
                    </a>
                    <span className="text-[#52504D] text-xs">·</span>
                    <a
                      href={`/verify?tx=${activePick.on_chain_tx_hash}`}
                      className="inline-flex items-center gap-1 text-xs font-mono text-emerald-400/60 hover:text-emerald-400 transition-colors"
                    >
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        <polyline points="9 12 11 14 15 10"/>
                      </svg>
                      Verify Proof
                    </a>
                  </div>
                ) : (
                  <span className="text-xs text-[#52504D] font-mono">Logging pending...</span>
                )}
              </div>
              
              <div className="flex gap-2">
                {activePick.protocols?.app_link && (
                  <a 
                    href={activePick.protocols.app_link}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#00ff88]/10 hover:bg-[#00ff88]/20 text-[#00ff88] border border-[#00ff88]/35 shadow-[0_0_10px_rgba(0,255,136,0.05)] transition-all duration-300"
                  >
                    Invest Pool
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
                
                <a 
                  href="https://t.me/YieldSageBot" 
                  target="_blank" 
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white/5 hover:bg-white/10 text-white/70 hover:text-white border border-white/10 transition-all duration-300"
                >
                  Chat with bot
                  <Send className="h-3 w-3" />
                </a>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
