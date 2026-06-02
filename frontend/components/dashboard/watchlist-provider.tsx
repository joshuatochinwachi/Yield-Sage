"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

interface WatchlistContextType {
  watchlist: Set<string>;
  toggleWatchlist: (id: string) => void;
  isWatched: (id: string) => boolean;
  clearWatchlist: () => void;
}

const WatchlistContext = createContext<WatchlistContextType | undefined>(undefined);

export function WatchlistProvider({ children }: { children: React.ReactNode }) {
  const [watchlist, setWatchlist] = useState<Set<string>>(new Set());
  const [isLoaded, setIsLoaded] = useState(false);

  // Load watchlist from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem("yieldsage_watchlist");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setWatchlist(new Set(parsed));
        }
      }
    } catch (e) {
      console.error("Error loading watchlist from localStorage:", e);
    }
    setIsLoaded(true);
  }, []);

  // Save watchlist to localStorage when it changes
  useEffect(() => {
    if (!isLoaded) return;
    try {
      localStorage.setItem("yieldsage_watchlist", JSON.stringify(Array.from(watchlist)));
    } catch (e) {
      console.error("Error saving watchlist to localStorage:", e);
    }
  }, [watchlist, isLoaded]);

  const toggleWatchlist = (id: string) => {
    setWatchlist((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const isWatched = (id: string) => {
    return watchlist.has(id);
  };

  const clearWatchlist = () => {
    setWatchlist(new Set());
  };

  return (
    <WatchlistContext.Provider
      value={{
        watchlist,
        toggleWatchlist,
        isWatched,
        clearWatchlist,
      }}
    >
      {children}
    </WatchlistContext.Provider>
  );
}

export function useWatchlist() {
  const context = useContext(WatchlistContext);
  if (context === undefined) {
    throw new Error("useWatchlist must be used within a WatchlistProvider");
  }
  return context;
}
