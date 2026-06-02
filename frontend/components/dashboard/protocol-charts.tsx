"use client";

import { useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { BarChart3, AlertCircle } from "lucide-react";

interface ProtocolChartsProps {
  data: any[] | undefined;
  isLoading: boolean;
}

function formatTVL(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
  return `$${value.toFixed(0)}`;
}

export function ProtocolCharts({ data, isLoading }: ProtocolChartsProps) {
  // Aggregate TVL by Protocol
  const aggregatedData = useMemo(() => {
    if (!data) return [];
    
    const map: Record<string, { name: string; tvl: number; poolCount: number }> = {};
    
    data.forEach((row) => {
      const protoName = row.protocol?.name || row.name || "Unknown";
      const tvl = row.tvl_usd ? parseFloat(row.tvl_usd) : 0;
      
      if (!map[protoName]) {
        map[protoName] = { name: protoName, tvl: 0, poolCount: 0 };
      }
      map[protoName].tvl += tvl;
      map[protoName].poolCount += 1;
    });
    
    return Object.values(map)
      .sort((a, b) => b.tvl - a.tvl)
      .slice(0, 8); // Top 8 protocols
  }, [data]);

  // Color palette for the bars (HSL tailored to dark/green aesthetic)
  const colors = [
    "#00ff88", // Active Accent
    "#05d9e8", // Cyan
    "#01012b", // Dark Blue Glow
    "#7000ff", // Purple
    "#ff007f", // Pink
    "#ffaa00", // Gold/Orange
    "#3b82f6", // Blue
    "#10b981", // Emerald
  ];

  return (
    <Card className="bg-black/40 backdrop-blur-xl border-white/5 overflow-hidden shadow-2xl relative group">
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#00ff88]/20 to-transparent" />
      
      <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-white/5 relative z-10">
        <div className="space-y-1">
          <CardTitle className="text-sm font-semibold text-white/90 flex items-center gap-2 tracking-wider uppercase font-sans">
            <BarChart3 className="h-4 w-4 text-[#00ff88]" />
            TVL Breakdown by Protocol
          </CardTitle>
          <CardDescription className="text-white/40 text-xs font-mono">
            Distribution of locked capital across top Mantle yield platforms
          </CardDescription>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6 relative z-10 space-y-4">
        {isLoading ? (
          <div className="h-64 flex flex-col items-center justify-center text-white/40 font-mono text-xs animate-pulse">
            <span>Aggregating on-chain metrics...</span>
          </div>
        ) : aggregatedData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-white/30 font-mono text-xs">
            No TVL data available.
          </div>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={aggregatedData}
                margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
              >
                <XAxis 
                  dataKey="name" 
                  stroke="#ffffff40" 
                  fontSize={10} 
                  tickLine={false}
                  axisLine={false}
                  dy={10}
                  className="font-mono text-[9px]"
                />
                <YAxis 
                  stroke="#ffffff40" 
                  fontSize={10} 
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={formatTVL}
                  dx={-5}
                  className="font-mono text-[9px]"
                />
                <Tooltip
                  cursor={{ fill: "rgba(255, 255, 255, 0.03)" }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const dataNode = payload[0].payload;
                      return (
                        <div className="bg-black/95 backdrop-blur-xl border border-white/10 p-3 rounded-xl shadow-2xl space-y-1">
                          <p className="text-xs font-semibold text-white">{dataNode.name}</p>
                          <p className="text-[11px] text-[#00ff88] font-mono">
                            TVL: <span className="font-bold">{formatTVL(dataNode.tvl)}</span>
                          </p>
                          <p className="text-[10px] text-white/40 font-mono">
                            Pools tracked: {dataNode.poolCount}
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar 
                  dataKey="tvl" 
                  radius={[4, 4, 0, 0]}
                  maxBarSize={45}
                >
                  {aggregatedData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={colors[index % colors.length]} 
                      className="transition-all duration-300 hover:opacity-80"
                      style={{
                        filter: `drop-shadow(0 0 6px ${colors[index % colors.length]}33)`
                      }}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        
        {/* DefiLlama Disclaimer */}
        <div className="flex items-start gap-2 p-3 bg-white/[0.02] border border-white/5 rounded-xl">
          <AlertCircle className="h-4 w-4 text-white/30 shrink-0 mt-0.5" />
          <p className="text-[10px] text-white/40 leading-relaxed font-mono">
            *Disclaimer: YieldSage tracks active yields and high-liquidity pools. Some low-TVL or inactive pools are filtered, so totals may differ from aggregate DefiLlama statistics.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
