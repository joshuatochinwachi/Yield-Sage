"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, ShieldCheck, ArrowRight, ExternalLink, Database, Cpu } from "lucide-react";
import { api } from "@/lib/api";

import { Suspense } from "react";

function VerifyContent() {
  const searchParams = useSearchParams();
  const txHash = searchParams?.get("tx");

  const [status, setStatus] = useState<"loading" | "verifying" | "success" | "error">("loading");
  const [data, setData] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [computedHash, setComputedHash] = useState("");

  useEffect(() => {
    if (!txHash) {
      setStatus("error");
      setErrorMsg("No transaction hash provided. Please provide a ?tx= query parameter.");
      return;
    }
    fetchData(txHash);
  }, [txHash]);

  const fetchData = async (hash: string) => {
    try {
      setStatus("loading");
      const res = await api.verifyRecommendation(hash);
      setData(res);
      setStatus("verifying");
    } catch (err: any) {
      console.error(err);
      setStatus("error");
      setErrorMsg(err.response?.data?.detail || "Failed to fetch recommendation data.");
    }
  };

  const handleVerify = async () => {
    if (!data) return;
    setStatus("verifying");
    
    // Simulate a slight delay for dramatic effect
    await new Promise((r) => setTimeout(r, 1500));

    try {
      // Create SHA-256 hash
      const encoder = new TextEncoder();
      const payloadData = encoder.encode(data.canonical_payload);
      const hashBuffer = await crypto.subtle.digest("SHA-256", payloadData);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");

      setComputedHash(hashHex);

      if (hashHex === data.data.recommendation_hash) {
        setStatus("success");
      } else {
        setStatus("error");
        setErrorMsg("Hash mismatch! The data appears to have been tampered with.");
      }
    } catch (err) {
      setStatus("error");
      setErrorMsg("Failed to compute hash.");
    }
  };

  // Auto-verify when data loads
  useEffect(() => {
    if (status === "verifying" && data) {
      handleVerify();
    }
  }, [status, data]);

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden flex flex-col items-center justify-center p-4">
      {/* Background gradients */}
      <div className="absolute top-0 inset-x-0 h-96 bg-gradient-to-b from-blue-900/20 to-transparent pointer-events-none" />
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-emerald-500/10 blur-[100px] rounded-full pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="z-10 w-full max-w-3xl space-y-8"
      >
        <div className="text-center space-y-4">
          <motion.div
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", bounce: 0.5 }}
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/5 border border-white/10 mb-4 backdrop-blur-md"
          >
            <ShieldCheck className="w-8 h-8 text-emerald-400" />
          </motion.div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-gradient-to-r from-white via-white/90 to-white/60 bg-clip-text text-transparent">
            Proof of Yield Verification
          </h1>
          <p className="text-white/60 max-w-xl mx-auto text-lg">
            YieldSage logs AI recommendations immutably on the Mantle blockchain. 
            Watch as we mathematically verify this recommendation's authenticity.
          </p>
        </div>

        {status === "error" && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-center space-y-3 backdrop-blur-md"
          >
            <XCircle className="w-10 h-10 text-red-400 mx-auto" />
            <h3 className="text-xl font-semibold text-red-400">Verification Failed</h3>
            <p className="text-red-300/80">{errorMsg}</p>
          </motion.div>
        )}

        {data && (status === "verifying" || status === "success") && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Input Data Card */}
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-md space-y-6"
            >
              <div className="flex items-center gap-3 text-white/80 border-b border-white/5 pb-4">
                <Database className="w-5 h-5 text-blue-400" />
                <h3 className="font-semibold text-lg">1. Original Payload</h3>
              </div>
              
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-white/40 block mb-1">Protocol</span>
                    <span className="font-medium">{data.data.protocols?.name}</span>
                  </div>
                  <div>
                    <span className="text-white/40 block mb-1">Pool</span>
                    <span className="font-medium">{data.data.protocols?.pool_name}</span>
                  </div>
                  <div>
                    <span className="text-white/40 block mb-1">APY</span>
                    <span className="text-emerald-400 font-medium">{data.data.apy_at_time}%</span>
                  </div>
                  <div>
                    <span className="text-white/40 block mb-1">Risk Profile</span>
                    <span className="font-medium uppercase tracking-wider text-xs px-2 py-1 bg-white/10 rounded-md">
                      {data.data.risk_tag}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-white/40 block mb-2 text-sm">Canonical JSON</span>
                  <div className="bg-black/50 border border-white/10 rounded-lg p-3 overflow-x-auto">
                    <pre className="text-xs text-blue-300/80 font-mono">
                      {data.canonical_payload}
                    </pre>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Hashing & Verification Card */}
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-md space-y-6 flex flex-col"
            >
              <div className="flex items-center gap-3 text-white/80 border-b border-white/5 pb-4">
                <Cpu className="w-5 h-5 text-emerald-400" />
                <h3 className="font-semibold text-lg">2. Cryptographic Hash</h3>
              </div>

              <div className="flex-1 flex flex-col justify-center space-y-8">
                {status === "verifying" ? (
                  <div className="text-center space-y-4 py-8">
                    <Loader2 className="w-10 h-10 text-emerald-400 animate-spin mx-auto" />
                    <p className="text-white/60 animate-pulse">Computing SHA-256 Hash...</p>
                  </div>
                ) : (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="space-y-6"
                  >
                    <div className="space-y-2">
                      <span className="text-white/40 block text-sm">Computed Local Hash</span>
                      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 overflow-hidden">
                        <p className="text-xs text-emerald-400 font-mono break-all leading-relaxed">
                          {computedHash}
                        </p>
                      </div>
                    </div>

                    <div className="flex justify-center text-white/40">
                      <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                      <span className="mx-2 text-sm font-medium">Perfect Match</span>
                    </div>

                    <div className="space-y-2">
                      <span className="text-white/40 block text-sm">On-Chain Target Hash</span>
                      <div className="bg-white/5 border border-white/10 rounded-lg p-3 overflow-hidden">
                        <p className="text-xs text-white/60 font-mono break-all leading-relaxed">
                          {data.data.recommendation_hash}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          </div>
        )}

        {status === "success" && data && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center pt-4"
          >
            <a 
              href={data.data.explorer_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="group relative inline-flex h-12 items-center justify-center overflow-hidden rounded-full bg-emerald-500 px-8 font-medium text-white transition-all hover:bg-emerald-400 hover:shadow-[0_0_40px_8px_rgba(16,185,129,0.3)]"
            >
              <span className="mr-2">View Verified Transaction on Mantlescan</span>
              <ExternalLink className="w-4 h-4 transition-transform group-hover:translate-x-1 group-hover:-translate-y-1" />
            </a>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4"><Loader2 className="w-10 h-10 text-emerald-400 animate-spin" /></div>}>
      <VerifyContent />
    </Suspense>
  );
}
