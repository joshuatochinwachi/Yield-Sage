import axios from "axios";
import { supabase } from "./supabase";

const API_URL = process.env.NEXT_PUBLIC_FAST_API_BACKEND_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor to inject Supabase JWT token for protected routes
apiClient.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  // Stats
  getOverviewStats: async () => {
    const { data } = await apiClient.get("/api/stats/overview");
    return data;
  },

  // Yields
  getLatestYields: async (riskTag?: string) => {
    const params = riskTag && riskTag !== "all" ? { risk_tag: riskTag } : {};
    const { data } = await apiClient.get("/api/yields/latest", { params });
    return data;
  },
  
  getLeaderboard: async (options: {
    page?: number;
    pageSize?: number;
    riskTag?: string;
    search?: string;
    minTvl?: number;
    minApy?: number;
  } = {}) => {
    const params: any = {
      page: options.page || 1,
      page_size: options.pageSize || 20,
    };
    if (options.riskTag && options.riskTag !== "all") params.risk_tag = options.riskTag;
    if (options.search) params.search = options.search;
    if (options.minTvl !== undefined && options.minTvl !== null) params.min_tvl = options.minTvl;
    if (options.minApy !== undefined && options.minApy !== null) params.min_apy = options.minApy;
    
    const { data } = await apiClient.get("/api/yields/leaderboard", { params });
    return data;
  },

  getYieldHistory: async (slug: string, days: number = 30) => {
    const { data } = await apiClient.get(`/api/yields/history/${slug}`, { params: { days } });
    return data;
  },

  // Recommendations
  getLatestRecommendations: async () => {
    const { data } = await apiClient.get("/api/recommendations/latest");
    return data;
  },

  // User & Paper Trades (Protected)
  getUserProfile: async () => {
    const { data } = await apiClient.get("/api/user/profile");
    return data;
  },

  getUserTrades: async () => {
    const { data } = await apiClient.get("/api/user/trades");
    return data;
  },
};
