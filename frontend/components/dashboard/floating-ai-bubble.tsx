"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Brain, MessageSquareCode, Sparkles } from "lucide-react";
import { useState } from "react";

export function FloatingAIBubble() {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <a
        href="https://t.me/YieldSageBot"
        target="_blank"
        rel="noopener noreferrer"
        className="relative block"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Glow effect */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-r from-[#00ff88] to-cyan-500 blur-md opacity-75 group-hover:opacity-100 transition-opacity animate-pulse" />

        {/* Dancing/Floating Bubble */}
        <motion.div
          animate={{
            y: [0, -8, 0],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="relative flex items-center justify-center w-14 h-14 rounded-full bg-black/80 border border-[#00ff88]/40 hover:border-[#00ff88] shadow-[0_0_20px_rgba(0,255,136,0.3)] backdrop-blur-xl group transition-all duration-300 hover:scale-105"
        >
          {/* Animated rings */}
          <span className="absolute inset-0 rounded-full border border-cyan-500/20 animate-ping opacity-75 pointer-events-none" />
          
          <Brain className="w-6 h-6 text-[#00ff88] group-hover:rotate-12 transition-transform duration-300" />
          <Sparkles className="absolute top-2.5 right-2.5 w-2.5 h-2.5 text-cyan-400 animate-pulse" />
        </motion.div>

        {/* Tooltip Label */}
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0, x: 20, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 10, scale: 0.95 }}
              className="absolute right-16 top-1/2 -translate-y-1/2 bg-black/90 backdrop-blur-xl border border-white/10 px-4 py-2 rounded-xl shadow-2xl pointer-events-none whitespace-nowrap"
            >
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00ff88] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00ff88]"></span>
                </span>
                <span className="text-xs font-semibold text-white tracking-wide font-sans">
                  Launch YieldSage AI Agent
                </span>
              </div>
              <span className="block text-[10px] text-white/50 font-mono mt-0.5 text-right">
                t.me/YieldSageBot
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </a>
    </div>
  );
}
