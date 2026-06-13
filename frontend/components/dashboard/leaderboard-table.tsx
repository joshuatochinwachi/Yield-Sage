"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Search, 
  SlidersHorizontal, 
  Star, 
  ChevronLeft, 
  ChevronRight, 
  ExternalLink,
  ArrowUpDown,
  Coins,
  ShieldAlert,
  Percent,
  TrendingUp as TrendUpIcon,
  Sparkles
} from "lucide-react";
import { useWatchlist } from "@/components/dashboard/watchlist-provider";

function formatTVL(value: number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function ProtocolIcon({ name, imageUrl }: { name: string; imageUrl?: string }) {
  const [error, setError] = useState(false);
  const initial = name ? name.charAt(0).toUpperCase() : "?";

  const getGradient = (str: string) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const colors = [
      "from-[#00ff88] to-emerald-600",
      "from-cyan-500 to-blue-600",
      "from-purple-500 to-indigo-600",
      "from-pink-500 to-rose-600",
      "from-amber-500 to-orange-600",
    ];
    return colors[Math.abs(hash) % colors.length];
  };

  if (imageUrl && !error) {
    return (
      <img
        src={imageUrl}
        alt={name}
        onError={() => setError(true)}
        className="w-8 h-8 rounded-full border border-white/10 bg-black/40 object-cover"
      />
    );
  }

  return (
    <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${getGradient(name)} flex items-center justify-center border border-white/10 shadow-[0_0_10px_rgba(255,255,255,0.05)] text-xs font-bold text-white uppercase`}>
      {initial}
    </div>
  );
}

function TrendPill({ label, value }: { label: string; value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return (
      <div className="flex flex-col items-center justify-center w-12 py-0.5 rounded bg-white/5 border border-white/5 text-white/30">
        <span className="text-[7px] text-white/20 uppercase tracking-wider font-mono">{label}</span>
        <span className="text-[9px] font-mono">-</span>
      </div>
    );
  }
  
  const isUp = value > 0.0001;
  const isDown = value < -0.0001;
  const formattedValue = value > 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`;
  
  return (
    <div className={`flex flex-col items-center justify-center w-12 py-0.5 rounded border text-[9px] font-mono transition-all duration-300 ${
      isUp 
        ? "text-[#00ff88] bg-[#00ff88]/10 border-[#00ff88]/20 shadow-[0_0_8px_rgba(0,255,136,0.05)]" 
        : isDown 
          ? "text-red-400 bg-red-500/10 border-red-500/20" 
          : "text-white/40 bg-white/5 border-white/5"
    }`}>
      <span className="text-[7px] text-white/30 uppercase tracking-wider font-mono">{label}</span>
      <span className="font-semibold">{formattedValue}</span>
    </div>
  );
}

type SortField = "tvl" | "apy" | "name" | "baseApy";
type SortOrder = "asc" | "desc";

export function LeaderboardTable() {
  const { isWatched, toggleWatchlist } = useWatchlist();
  
  // State variables for filters and pagination
  const [activeTab, setActiveTab] = useState<"all" | "watchlist">("all");
  const [riskFilter, setRiskFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [minTvlInput, setMinTvlInput] = useState<string>("");
  const [minApyInput, setMinApyInput] = useState<string>("");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState<boolean>(false);
  
  // Sorting state
  const [sortField, setSortField] = useState<SortField>("tvl");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 20;

  const [simModalOpen, setSimModalOpen] = useState(false);
  const [simPoolAddr, setSimPoolAddr] = useState("");
  const [simPoolName, setSimPoolName] = useState("");
  const [simAmount, setSimAmount] = useState("1000");

  // Debounced filters to pass to API
  const minTvl = minTvlInput ? parseFloat(minTvlInput) : undefined;
  const minApy = minApyInput ? parseFloat(minApyInput) : undefined;

  // Query parameters: if watchlist is active, fetch up to 500 rows to do client-side filtering and local pagination
  const queryParams = useMemo(() => {
    if (activeTab === "watchlist") {
      return {
        page: 1,
        pageSize: 500, // Fetch large batch to filter locally
        riskTag: riskFilter !== "all" ? riskFilter : undefined,
        search: searchQuery || undefined,
        minTvl,
        minApy,
      };
    }
    return {
      page: currentPage,
      pageSize,
      riskTag: riskFilter !== "all" ? riskFilter : undefined,
      search: searchQuery || undefined,
      minTvl,
      minApy,
    };
  }, [activeTab, currentPage, riskFilter, searchQuery, minTvl, minApy]);

  const { data, isLoading } = useQuery({
    queryKey: ["leaderboard", queryParams, activeTab],
    queryFn: () => api.getLeaderboard(queryParams),
    refetchInterval: 60000,
  });

  // Client-side processing (filtering by watchlist, sorting)
  const processedRows = useMemo(() => {
    if (!data?.data) return [];
    let rows = [...data.data];

    // 1. Watchlist Filter (if on watchlist tab)
    if (activeTab === "watchlist") {
      rows = rows.filter((row: any) => isWatched(row.protocol_id));
    }

    // 2. Client-side Sorting
    rows.sort((a: any, b: any) => {
      let valA: any;
      let valB: any;

      if (sortField === "tvl") {
        valA = a.tvl_usd ?? 0;
        valB = b.tvl_usd ?? 0;
      } else if (sortField === "apy") {
        valA = a.apy ?? 0;
        valB = b.apy ?? 0;
      } else if (sortField === "baseApy") {
        valA = a.base_apy ?? 0;
        valB = b.base_apy ?? 0;
      } else if (sortField === "name") {
        const protoA = a.protocol || {};
        const protoB = b.protocol || {};
        valA = (protoA.name || a.name || "").toLowerCase();
        valB = (protoB.name || b.name || "").toLowerCase();
      }

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });

    return rows;
  }, [data, activeTab, isWatched, sortField, sortOrder]);

  // Client-side pagination for Watchlist tab
  const paginatedRows = useMemo(() => {
    if (activeTab !== "watchlist") return processedRows;
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return processedRows.slice(start, end);
  }, [processedRows, activeTab, currentPage]);

  const totalPages = useMemo(() => {
    if (activeTab !== "watchlist") return data?.total_pages || 0;
    return Math.ceil(processedRows.length / pageSize);
  }, [processedRows, activeTab, data]);

  const totalItems = useMemo(() => {
    if (activeTab !== "watchlist") return data?.total || 0;
    return processedRows.length;
  }, [processedRows, activeTab, data]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const resetFilters = () => {
    setRiskFilter("all");
    setSearchQuery("");
    setMinTvlInput("");
    setMinApyInput("");
    setCurrentPage(1);
  };

  const riskColors: Record<string, string> = {
    stable: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    moderate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    aggressive: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  return (
    <Card className="bg-black/40 backdrop-blur-xl border-white/5 overflow-hidden shadow-2xl relative">
      {/* Dynamic top accent light */}
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#00ff88]/20 to-transparent" />

      <CardHeader className="flex flex-col space-y-4 pb-6 border-b border-white/5 relative z-10">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="space-y-1">
            <CardTitle className="text-xl font-light text-white tracking-tight flex items-center gap-2">
              <Coins className="h-5 w-5 text-[#00ff88]" />
              Mantle Yield Opportunities
            </CardTitle>
            <p className="text-xs text-white/40 font-mono">
              Real-time yield snapshots aggregated across the Mantle network.
            </p>
          </div>

          {/* Toggle Tab (All vs Watchlist) */}
          <div className="flex bg-white/5 p-1 rounded-xl border border-white/10">
            <button
              onClick={() => {
                setActiveTab("all");
                setCurrentPage(1);
              }}
              className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all duration-300 ${
                activeTab === "all"
                  ? "bg-[rgba(0,255,136,0.15)] text-[#00ff88] border border-[rgba(0,255,136,0.2)]"
                  : "text-white/50 hover:text-white border border-transparent"
              }`}
            >
              All Pools
            </button>
            <button
              onClick={() => {
                setActiveTab("watchlist");
                setCurrentPage(1);
              }}
              className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all duration-300 flex items-center gap-1.5 ${
                activeTab === "watchlist"
                  ? "bg-[rgba(0,255,136,0.15)] text-[#00ff88] border border-[rgba(0,255,136,0.2)]"
                  : "text-white/50 hover:text-white border border-transparent"
              }`}
            >
              <Star className="h-3.5 w-3.5 fill-current" />
              Watchlist
            </button>
          </div>
        </div>

        {/* Filters and Search Panel */}
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
              <input
                type="text"
                placeholder="Search protocol, pool or asset..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full pl-10 pr-4 py-2 bg-white/5 hover:bg-white/[0.08] focus:bg-white/[0.08] border border-white/10 rounded-xl text-sm text-white placeholder-white/30 focus:outline-none focus:ring-1 focus:ring-[#00ff88]/50 focus:border-[#00ff88]/30 transition-all font-mono"
              />
            </div>

            {/* Risk Badges selection */}
            <div className="flex items-center gap-1.5 p-1 bg-white/5 rounded-xl border border-white/10 overflow-x-auto">
              {["all", "stable", "moderate", "aggressive"].map((filter) => (
                <button
                  key={filter}
                  onClick={() => {
                    setRiskFilter(filter);
                    setCurrentPage(1);
                  }}
                  className={`px-3 py-1 text-[11px] font-medium rounded-lg capitalize transition-all duration-300 whitespace-nowrap ${
                    riskFilter === filter
                      ? "bg-white/10 text-white border border-white/10"
                      : "text-white/40 hover:text-white border border-transparent"
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>

            {/* Toggle advanced filters */}
            <button
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className={`px-3 py-2 rounded-xl border flex items-center justify-center gap-1.5 text-xs font-semibold font-mono transition-all duration-300 ${
                showAdvancedFilters
                  ? "bg-[#00ff88]/10 border-[#00ff88]/30 text-[#00ff88]"
                  : "bg-white/5 border-white/10 text-white/60 hover:text-white"
              }`}
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Filters
            </button>
          </div>

          {/* Advanced Sliders / Filters panel */}
          {showAdvancedFilters && (
            <div className="p-4 bg-black/40 border border-white/5 rounded-2xl grid grid-cols-1 sm:grid-cols-3 gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="space-y-1.5">
                <label className="text-[10px] font-semibold text-white/50 uppercase tracking-wider font-mono">Min TVL ($)</label>
                <input
                  type="number"
                  placeholder="e.g. 50000"
                  value={minTvlInput}
                  onChange={(e) => {
                    setMinTvlInput(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-white placeholder-white/20 focus:outline-none focus:ring-1 focus:ring-[#00ff88]/40 font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] font-semibold text-white/50 uppercase tracking-wider font-mono">Min APY (%)</label>
                <input
                  type="number"
                  placeholder="e.g. 5.0"
                  value={minApyInput}
                  onChange={(e) => {
                    setMinApyInput(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-white placeholder-white/20 focus:outline-none focus:ring-1 focus:ring-[#00ff88]/40 font-mono"
                />
              </div>

              <div className="flex items-end">
                <button
                  onClick={resetFilters}
                  className="w-full py-1.5 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-xs font-semibold rounded-lg border border-white/10 transition-all font-mono"
                >
                  Clear Filters
                </button>
              </div>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0 relative z-10">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-[10px] text-white/40 uppercase tracking-wider bg-black/60 border-b border-white/5">
              <tr>
                <th className="px-4 py-4 text-center w-10"></th>
                <th 
                  onClick={() => handleSort("name")}
                  className="px-5 py-4 font-semibold font-mono cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    Protocol / Pool
                    <ArrowUpDown className="h-3 w-3 opacity-60" />
                  </div>
                </th>
                <th className="px-5 py-4 font-semibold font-mono">Asset</th>
                <th className="px-5 py-4 font-semibold font-mono">Risk</th>
                <th 
                  onClick={() => handleSort("apy")}
                  className="px-5 py-4 font-semibold font-mono text-right cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center justify-end gap-1.5">
                    Current APY
                    <ArrowUpDown className="h-3 w-3 opacity-60" />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort("baseApy")}
                  className="px-5 py-4 font-semibold font-mono text-right cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center justify-end gap-1.5">
                    APY Breakdown
                    <ArrowUpDown className="h-3 w-3 opacity-60" />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort("tvl")}
                  className="px-5 py-4 font-semibold font-mono text-right cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center justify-end gap-1.5">
                    TVL
                    <ArrowUpDown className="h-3 w-3 opacity-60" />
                  </div>
                </th>
                <th className="px-5 py-4 font-semibold font-mono text-center">Trends (1D/7D/30D)</th>
                <th className="px-6 py-4 font-semibold font-mono text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="flex space-x-1.5">
                        <div className="w-2.5 h-2.5 bg-[#00ff88] rounded-full animate-bounce [animation-delay:-0.3s]" />
                        <div className="w-2.5 h-2.5 bg-[#00ff88] rounded-full animate-bounce [animation-delay:-0.15s]" />
                        <div className="w-2.5 h-2.5 bg-[#00ff88] rounded-full animate-bounce" />
                      </div>
                      <span className="text-white/40 text-xs font-mono uppercase tracking-widest">Querying database...</span>
                    </div>
                  </td>
                </tr>
              ) : paginatedRows.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-16 text-center text-white/40 font-mono">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <ShieldAlert className="h-8 w-8 text-white/20" />
                      <span>No yield opportunities found matching criteria.</span>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedRows.map((row: any, i) => {
                  const protocol = row.protocol || {};
                  
                  const isRowWatched = isWatched(row.protocol_id);

                  // Extract pool address for explorer links
                  const poolAddr = protocol.pool_address || row.pool_address;
                  const explorerLink = poolAddr 
                    ? (poolAddr.startsWith("http") ? poolAddr : `https://mantlescan.xyz/address/${poolAddr}`)
                    : null;

                  return (
                    <tr key={`${row.protocol_id}-${i}`} className="hover:bg-white/[0.03] transition-all duration-200 group">
                      {/* Watchlist Star */}
                      <td className="px-4 py-4 text-center">
                        <button
                          onClick={() => toggleWatchlist(row.protocol_id)}
                          className={`hover:scale-115 active:scale-95 transition-all ${
                            isRowWatched
                              ? "text-yellow-400 filter drop-shadow-[0_0_8px_rgba(250,204,21,0.5)]"
                              : "text-white/20 hover:text-white/60"
                          }`}
                        >
                          <Star className="h-4 w-4 fill-current" />
                        </button>
                      </td>

                      {/* Protocol & Pool */}
                      <td className="px-5 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <ProtocolIcon name={protocol.name || row.name || "Protocol"} imageUrl={protocol.image_url || row.image_url} />
                          <div>
                            <div className="font-semibold text-white group-hover:text-[#00ff88] transition-colors text-sm font-sans flex items-center gap-1">
                              {explorerLink ? (
                                <a 
                                  href={explorerLink} 
                                  target="_blank" 
                                  rel="noopener noreferrer" 
                                  className="hover:underline flex items-center gap-1 text-white group-hover:text-[#00ff88]"
                                >
                                  {protocol.name || row.name}
                                  <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                                </a>
                              ) : (
                                <span>{protocol.name || row.name}</span>
                              )}
                            </div>
                            <div className="text-white/40 text-[10px] uppercase font-mono tracking-wider">
                              {protocol.pool_name || row.pool_name || "Lending pool"}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Asset */}
                      <td className="px-5 py-4 whitespace-nowrap">
                        <span className="text-white font-medium bg-white/5 px-2 py-1 rounded-md border border-white/5 font-mono">
                          {row.asset}
                        </span>
                      </td>

                      {/* Risk Tier Badge */}
                      <td className="px-5 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase border ${riskColors[protocol.risk_tag || row.risk_tag] || "bg-white/10 text-white/70"}`}>
                          {protocol.risk_tag || row.risk_tag}
                        </span>
                      </td>

                      {/* Current APY */}
                      <td className="px-5 py-4 whitespace-nowrap text-right">
                        <div className="text-base font-bold text-[#00ff88] font-mono drop-shadow-[0_0_8px_rgba(0,255,136,0.35)]">
                          {row.apy !== null ? `${row.apy.toFixed(2)}%` : "N/A"}
                        </div>
                      </td>

                      {/* APY Breakdown */}
                      <td className="px-5 py-4 whitespace-nowrap text-right">
                        <div className="flex flex-col items-end text-[10px] text-white/50 font-mono">
                          <div>Base: <span className="text-white/75 font-semibold">{(row.base_apy ?? 0).toFixed(2)}%</span></div>
                          <div>Rewards: <span className="text-white/75 font-semibold">{(row.reward_apy ?? 0).toFixed(2)}%</span></div>
                          {row.reward_tokens && (
                            <span className="text-[8px] px-1 rounded bg-[#00ff88]/10 text-[#00ff88]/80 mt-0.5 border border-[#00ff88]/20 truncate max-w-[120px]" title={row.reward_tokens}>
                              {row.reward_tokens}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* TVL */}
                      <td className="px-5 py-4 whitespace-nowrap text-right">
                        <div className="text-white/80 font-mono text-xs font-semibold">
                          {formatTVL(row.tvl_usd)}
                        </div>
                      </td>

                      {/* Trends (1D / 7D / 30D) */}
                      <td className="px-5 py-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center gap-1">
                          <TrendPill label="1d" value={row.apy_1d} />
                          <TrendPill label="7d" value={row.apy_7d} />
                          <TrendPill label="30d" value={row.apy_30d} />
                        </div>
                      </td>

                      {/* Action (Invest Link & Simulate) */}
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center gap-2">
                          {protocol.app_link || row.app_link ? (
                            <a
                              href={protocol.app_link || row.app_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#00ff88]/10 hover:bg-[#00ff88]/20 text-[#00ff88] border border-[#00ff88]/25 hover:border-[#00ff88]/50 shadow-[0_0_12px_rgba(0,255,136,0.08)] transition-all duration-300 hover:-translate-y-0.5"
                              title="Go to protocol DApp to invest"
                            >
                              Invest
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-xs text-white/20 font-mono">-</span>
                          )}
                          <button
                            onClick={() => {
                              setSimPoolAddr(poolAddr || "");
                              setSimPoolName(`${protocol.name || "Unknown"} (${row.asset || "Pool"})`);
                              setSimAmount("1000");
                              setSimModalOpen(true);
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#a78bfa]/10 hover:bg-[#a78bfa]/20 text-[#a78bfa] border border-[#a78bfa]/25 hover:border-[#a78bfa]/50 shadow-[0_0_12px_rgba(167,139,250,0.08)] transition-all duration-300 hover:-translate-y-0.5 cursor-pointer"
                            title="Simulate trade in Telegram"
                          >
                            Simulate
                            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M22 2L11 13" />
                              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Section */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-white/5 bg-black/20 relative z-10">
            <div className="text-xs text-white/40 font-mono">
              Showing <span className="text-white/70 font-semibold">{paginatedRows.length}</span> of{" "}
              <span className="text-white/70 font-semibold">{totalItems}</span> yield opportunities
            </div>
            
            <div className="flex items-center space-x-1">
              <button
                disabled={currentPage === 1 || isLoading}
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                className="p-2 text-white/50 hover:text-white disabled:text-white/10 disabled:pointer-events-none hover:bg-white/5 rounded-lg border border-white/10 disabled:border-white/5 transition-all"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              
              <div className="flex items-center space-x-1.5 px-2">
                {Array.from({ length: totalPages }).map((_, i) => {
                  const pageNum = i + 1;
                  // Show current page, first, last, and pages adjacent to current page
                  if (
                    pageNum === 1 || 
                    pageNum === totalPages || 
                    Math.abs(pageNum - currentPage) <= 1
                  ) {
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`w-7 h-7 flex items-center justify-center text-xs font-semibold rounded-lg border font-mono transition-all duration-300 ${
                          currentPage === pageNum
                            ? "bg-[#00ff88]/10 border-[#00ff88]/40 text-[#00ff88] shadow-[0_0_10px_rgba(0,255,136,0.1)]"
                            : "bg-transparent border-white/10 text-white/40 hover:text-white hover:border-white/20"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  } else if (
                    pageNum === 2 || 
                    pageNum === totalPages - 1
                  ) {
                    return <span key={pageNum} className="text-white/20 text-xs">...</span>;
                  }
                  return null;
                })}
              </div>

              <button
                disabled={currentPage === totalPages || isLoading}
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                className="p-2 text-white/50 hover:text-white disabled:text-white/10 disabled:pointer-events-none hover:bg-white/5 rounded-lg border border-white/10 disabled:border-white/5 transition-all"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Price Data Disclaimer */}
        <div className="flex items-start gap-2 px-6 py-3.5 bg-white/[0.01] border-t border-white/5 relative z-10">
          <ShieldAlert className="h-3.5 w-3.5 text-white/30 shrink-0 mt-0.5" />
          <p className="text-[10px] text-white/30 leading-relaxed font-mono">
            *Disclaimer: These TVL and APY metrics represent active on-chain indexes integrated with YieldSage. Values may slightly differ from the official protocol applications due to differences in pricing sources, data collection frequencies, or aggregation methodologies.
          </p>
        </div>
      </CardContent>
      {simModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 transition-all duration-300">
          <div className="bg-[#0a0a0c] border border-white/10 rounded-2xl p-6 max-w-sm w-full mx-auto shadow-2xl relative z-55">
            <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-indigo-400" />
              Simulate Paper Trade
            </h3>
            <p className="text-xs text-white/60 mb-4 leading-relaxed">
              How much USD would you like to simulate investing in <span className="text-white font-semibold">{simPoolName}</span>?
            </p>
            <div className="relative mb-5">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/40 text-xs font-mono">$</span>
              <input
                type="number"
                value={simAmount}
                onChange={(e) => setSimAmount(e.target.value)}
                placeholder="1000"
                className="w-full bg-white/5 border border-white/10 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 rounded-xl pl-8 pr-4 py-2.5 text-sm font-mono text-white placeholder-white/20 outline-none transition-all"
                autoFocus
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setSimModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-white/10 hover:bg-white/5 text-white/70 transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setSimModalOpen(false);
                  const cleanAddr = simPoolAddr.match(/0x[a-fA-F0-9]{40}/)?.[0] || simPoolAddr;
                  const telegramUrl = `https://t.me/YieldSageBot?text=${encodeURIComponent(`/trade address=${cleanAddr} amount=${simAmount} token=${simPoolName}`)}`;
                  window.open(telegramUrl, "_blank", "noopener,noreferrer");
                }}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-all cursor-pointer"
              >
                Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
