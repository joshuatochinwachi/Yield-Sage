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
  
  getLeaderboard: async (limit: number = 50, offset: number = 0, riskTag?: string) => {
    const params: any = { limit, offset };
    if (riskTag && riskTag !== "all") params.risk_tag = riskTag;
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
