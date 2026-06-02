"use client";

import { useEffect, useState } from "react";
import { Cookie, X } from "lucide-react";

export function StorageConsent() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check if consent has already been given/declined
    const consent = localStorage.getItem("yieldsage_storage_consent");
    if (!consent) {
      // Show banner after a brief delay
      const timer = setTimeout(() => setIsVisible(true), 1500);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem("yieldsage_storage_consent", "accepted");
    setIsVisible(false);
  };

  const handleDecline = () => {
    localStorage.setItem("yieldsage_storage_consent", "declined");
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-6 left-6 right-6 md:left-auto md:right-6 md:w-[420px] z-50 animate-in slide-in-from-bottom-5 duration-500">
      <div className="bg-black/60 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-[0_10px_50px_rgba(0,0,0,0.8),0_0_20px_rgba(0,255,136,0.05)] relative overflow-hidden group">
        {/* Subtle glow border */}
        <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-[#00ff88]/30 to-transparent" />
        
        <button
          onClick={handleDecline}
          className="absolute top-4 right-4 text-white/40 hover:text-white transition-colors"
          aria-label="Close banner"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex gap-4 items-start">
          <div className="p-3 bg-[#00ff88]/10 rounded-xl border border-[#00ff88]/20 text-[#00ff88] flex-shrink-0 shadow-[0_0_15px_rgba(0,255,136,0.1)]">
            <Cookie className="h-5 w-5 animate-pulse" />
          </div>
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-white tracking-wide uppercase">Local Storage Preference</h4>
            <p className="text-xs text-white/60 leading-relaxed font-mono">
              We use local storage (like cookies) to store your watchlist and page preferences locally on your browser. No personal data is collected or sent to our servers.
            </p>
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleAccept}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-[#00ff88]/10 hover:bg-[#00ff88]/20 text-[#00ff88] border border-[#00ff88]/30 hover:border-[#00ff88]/50 shadow-[0_0_10px_rgba(0,255,136,0.05)] transition-all duration-300"
              >
                Accept All
              </button>
              <button
                onClick={handleDecline}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-white/5 hover:bg-white/10 text-white/50 hover:text-white border border-transparent transition-all duration-300"
              >
                Essentials Only
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
