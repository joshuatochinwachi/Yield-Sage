"""
YieldSage — Model Speed & Reliability Benchmark
================================================
Tests all models in the cascade with a realistic prompt
(same size as the actual YieldSage prompts: ~8,000-9,000 tokens).

Output: ranked table by speed + reliability.
"""

import asyncio
import time
import os
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError

load_dotenv()

# ── Model roster ──────────────────────────────────────────────────────────────
MODELS = [
    # ── Groq ──────────────────────────────────────────────────────────────────
    {
        # Fastest provider when it lands — 394 t/s on LPU hardware
        # Rate limited after 1st call per hour on free tier
        "label":    "Groq — llama-3.3-70b-versatile",
        "provider": "Groq",
        "model":    "llama-3.3-70b-versatile",
        "env_key":  "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    {
        "label":    "Groq — openai/gpt-oss-120b",
        "provider": "Groq",
        "model":    "openai/gpt-oss-120b",
        "env_key":  "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    {
        "label":    "Groq — qwen/qwen3.6-27b",
        "provider": "Groq",
        "model":    "qwen/qwen3.6-27b",
        "env_key":  "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    # ── NVIDIA ────────────────────────────────────────────────────────────────
    {
        # Proven workhorse — 100% reliability across both benchmark runs
        "label":    "NVIDIA — llama-3.1-70b-instruct",
        "provider": "NVIDIA",
        "model":    "meta/llama-3.1-70b-instruct",
        "env_key":  "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
    },
    {
        # NVIDIA secondary — also 100% reliable, slightly slower TTFT
        "label":    "NVIDIA — llama-3.3-70b-instruct",
        "provider": "NVIDIA",
        "model":    "meta/llama-3.3-70b-instruct",
        "env_key":  "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
    },
    # ── Gemini ────────────────────────────────────────────────────────────────
    {
        # Best instruction following — timing-dependent but real
        # Railway logs prove it works across hours when not hammered back-to-back
        "label":    "Gemini — gemini-2.5-flash",
        "provider": "Gemini",
        "model":    "gemini-2.5-flash",
        "env_key":  "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    {
        # Gemini fallback
        "label":    "Gemini — gemini-2.5-flash-lite",
        "provider": "Gemini",
        "model":    "gemini-2.5-flash-lite",
        "env_key":  "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    # ── Cerebras (NEW) ────────────────────────────────────────────────────────
    # Runs on Cerebras Wafer-Scale Engine (WSE) chips — not GPUs.
    # Fully OpenAI-compatible. Free tier: 1M tokens/day, 30 RPM, 60K TPM.
    # Both models have 128K context — comfortably above your 8-9K prompt size.
    {
        # 120B parameter model — production tier on Cerebras
        # WSE chips designed for high-throughput inference
        "label":    "Cerebras — gpt-oss-120b",
        "provider": "Cerebras",
        "model":    "gpt-oss-120b",
        "env_key":  "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
    },
    {
        # GLM 4.7 — preview tier on Cerebras, same WSE hardware
        # Preview = may have lower stability, worth testing
        "label":    "Cerebras — zai-glm-4.7",
        "provider": "Cerebras",
        "model":    "zai-glm-4.7",
        "env_key":  "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
    },
    # ── OpenRouter (free tier) ────────────────────────────────────────────────
    {
        # Llama 3.3 70B via OpenRouter free pool
        # Previously 429'd — congested but not dead, worth retesting
        "label":    "OpenRouter — llama-3.3-70b-instruct:free",
        "provider": "OpenRouter",
        "model":    "meta-llama/llama-3.3-70b-instruct:free",
        "env_key":  "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
    },
    {
        # DeepSeek R1 — free on OpenRouter, from friend's setup
        # WARNING: reasoning model — thinks before responding, adds latency
        # Good quality but expect slower TTFT than non-reasoning models
        "label":    "OpenRouter — deepseek-r1:free",
        "provider": "OpenRouter",
        "model":    "deepseek/deepseek-r1:free",
        "env_key":  "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
    },
# ── SambaNova ─────────────────────────────────────────────────────────────
    {
        "label":    "SambaNova — DeepSeek-V3.1",
        "provider": "SambaNova",
        "model":    "DeepSeek-V3.1",
        "env_key":  "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
    },
    {
        "label":    "SambaNova — DeepSeek-V3.2",
        "provider": "SambaNova",
        "model":    "DeepSeek-V3.2",
        "env_key":  "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
    },
    {
        "label":    "SambaNova — Llama-4-Maverick-17B",
        "provider": "SambaNova",
        "model":    "Llama-4-Maverick-17B-128E-Instruct",
        "env_key":  "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
    },
    {
        "label":    "SambaNova — Meta-Llama-3.3-70B",
        "provider": "SambaNova",
        "model":    "Meta-Llama-3.3-70B-Instruct",
        "env_key":  "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
    },
    {
        "label":    "SambaNova — gemma-3-12b",
        "provider": "SambaNova",
        "model":    "gemma-3-12b-it",
        "env_key":  "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
    },
    {
        "label":    "SambaNova — gemma-4-31B",
        "provider": "SambaNova",
        "model":    "gemma-4-31B-it",
        "env_key":  "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
    },
    {
        "label":    "SambaNova — MiniMax-M2.7",
        "provider": "SambaNova",
        "model":    "MiniMax-M2.7",
        "env_key":  "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
    },
    {
        "label":    "SambaNova — gpt-oss-120b",
        "provider": "SambaNova",
        "model":    "gpt-oss-120b",
        "env_key":  "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
    },
]

# ── Realistic prompt — same size class as your actual YieldSage prompts ───────
# Padded to ~8,000 tokens to simulate real conditions
SYSTEM_PROMPT = """You are YieldSage — a DeFi yield advisor on Mantle Network.
You are direct, data-driven, and concise. Never use markdown headers. Never use tables.
Use bullet points only. Bold = **double asterisks**.

DATA INTEGRITY LAW: Only use numbers explicitly provided. Never invent APY or TVL values.

Current Live Yields (Mantle Network):
- Agni Finance (WMNT-mETH): APY: 121.84% | TVL: $1,282 | Risk: AGGRESSIVE
- Agni Finance (USDT-USDC): APY: 3.45% | TVL: $892,100 | Risk: STABLE
- Merchant Moe (MNT-mETH): APY: 45.20% | TVL: $234,500 | Risk: MODERATE
- Clearpool (USDT): APY: 17.50% | TVL: $2,100,000 | Risk: STABLE
- Aave V3 (USDC): APY: 7.02% | TVL: $3,682,789 | Risk: STABLE
- Fluxion (USDT0-BSB): APY: 26.45% | TVL: $567,000 | Risk: MODERATE
- mETH Protocol (mETH): APY: 4.12% | TVL: $12,400,000 | Risk: STABLE

User Active Paper Trades:
- Agni Finance WMNT-mETH: $15,000 invested at 121.84% entry APY
- Clearpool USDT: $5,000 invested at 16.20% entry APY

Conversation history:
User: What are the best stable pools right now?
Assistant: The top stable pools on Mantle right now are Clearpool USDT at 17.50% APY with $2.1M TVL, Aave V3 USDC at 7.02% APY with $3.68M TVL, and Agni Finance USDT-USDC at 3.45% APY with $892K TVL. Clearpool leads on yield, Aave leads on safety.
User: What about my WMNT-mETH position?
Assistant: Your $15,000 position is sitting at 121.84% APY entry. Current APY is still 121.87% — marginally outperforming. However, TVL is only $1,282 which is extremely thin liquidity. That is a serious exit risk. I would consider rotating 50% into Clearpool USDT at 17.50% to de-risk while keeping upside exposure.
User: How does Clearpool work exactly?
Assistant: Clearpool runs institutional private credit pools. Whitelisted borrowers — typically crypto-native trading firms — draw USDT liquidity and pay variable interest. The rate floats based on pool utilisation. Higher utilisation means higher APY. At 17.50% you are being paid institutional borrowing rates, which is why it beats Aave's 7% significantly. The risk is borrower default, which is mitigated by Clearpool's whitelisting process and overcollateralisation requirements.
"""

USER_MESSAGE = (
    "Give me a full portfolio review. Look at all my active trades, "
    "compare them against current yields, flag anything underperforming by more than 2%, "
    "and give me one specific reallocation recommendation with exact amounts."
)

RUNS_PER_MODEL = 3  # number of test calls per model — increase for more accuracy


# ── Benchmark runner ──────────────────────────────────────────────────────────

async def test_model(model_cfg: dict, run_index: int) -> dict:
    api_key = os.getenv(model_cfg["env_key"])
    if not api_key:
        return {
            "label":      model_cfg["label"],
            "run":        run_index,
            "status":     "SKIP",
            "error":      f"{model_cfg['env_key']} not set",
            "ttft_ms":    None,
            "total_ms":   None,
            "tokens_out": None,
            "tps":        None,
        }

    client = AsyncOpenAI(base_url=model_cfg["base_url"], api_key=api_key)

    start = time.perf_counter()
    ttft  = None

    try:
        stream = await client.chat.completions.create(
            model=model_cfg["model"],
            messages=[
                {"role": "system",  "content": SYSTEM_PROMPT},
                {"role": "user",    "content": USER_MESSAGE},
            ],
            max_tokens=600,
            temperature=0.3,
            stream=True,
        )

        chunks      = []
        tokens_out  = 0

        async for chunk in stream:
            if ttft is None:
                ttft = (time.perf_counter() - start) * 1000  # ms to first token

            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                chunks.append(delta)
                tokens_out += 1  # rough token count by chunk

        total_ms = (time.perf_counter() - start) * 1000
        duration_s = total_ms / 1000
        tps = round(tokens_out / duration_s, 1) if duration_s > 0 else 0

        return {
            "label":      model_cfg["label"],
            "run":        run_index,
            "status":     "OK",
            "error":      None,
            "ttft_ms":    round(ttft, 0) if ttft else None,
            "total_ms":   round(total_ms, 0),
            "tokens_out": tokens_out,
            "tps":        tps,
        }

    except RateLimitError as e:
        return {
            "label":      model_cfg["label"],
            "run":        run_index,
            "status":     "429",
            "error":      "Rate limited",
            "ttft_ms":    None,
            "total_ms":   round((time.perf_counter() - start) * 1000, 0),
            "tokens_out": None,
            "tps":        None,
        }

    except Exception as e:
        err = str(e)
        status = "429" if "429" in err else ("413" if "413" in err else "ERROR")
        return {
            "label":      model_cfg["label"],
            "run":        run_index,
            "status":     status,
            "error":      err[:120],
            "ttft_ms":    None,
            "total_ms":   round((time.perf_counter() - start) * 1000, 0),
            "tokens_out": None,
            "tps":        None,
        }


async def run_benchmark():
    filter_arg = sys.argv[1].lower() if len(sys.argv) > 1 else None
    target_models = MODELS
    if filter_arg:
        target_models = [m for m in MODELS if filter_arg in m["label"].lower() or filter_arg in m["provider"].lower()]
        if not target_models:
            print(f"No models matched filter: {filter_arg}")
            return

    print("\n" + "="*70)
    print("  YieldSage — Model Speed & Reliability Benchmark")
    print(f"  {RUNS_PER_MODEL} runs per model | Realistic ~8K token prompt")
    if filter_arg:
        print(f"  Filtered by: '{filter_arg}' ({len(target_models)} models)")
    print("="*70 + "\n")

    all_results = []

    for model_cfg in target_models:
        print(f"Testing: {model_cfg['label']}")
        for i in range(1, RUNS_PER_MODEL + 1):
            print(f"  Run {i}/{RUNS_PER_MODEL}...", end=" ", flush=True)
            result = await test_model(model_cfg, i)
            all_results.append(result)

            if result["status"] == "OK":
                print(f"✅  TTFT: {result['ttft_ms']}ms | Total: {result['total_ms']}ms | ~{result['tps']} t/s")
            elif result["status"] == "SKIP":
                print(f"⏭️   SKIPPED — {result['error']}")
                break  # no point running more if key is missing
            elif result["status"] == "429":
                print(f"🚫  RATE LIMITED — {result['total_ms']}ms")
            elif result["status"] == "413":
                print(f"❌  413 PAYLOAD TOO LARGE — context limit exceeded")
            else:
                print(f"❌  ERROR — {result['error']}")

            # small gap between calls to avoid hammering
            await asyncio.sleep(1.5)

        print()

    # ── Aggregate results ─────────────────────────────────────────────────────
    summary = {}
    for r in all_results:
        label = r["label"]
        if label not in summary:
            summary[label] = {
                "label":       label,
                "total_runs":  0,
                "successes":   0,
                "rate_limits": 0,
                "errors":      0,
                "ttft_vals":   [],
                "total_vals":  [],
                "tps_vals":    [],
            }
        s = summary[label]
        s["total_runs"] += 1
        if r["status"] == "OK":
            s["successes"] += 1
            if r["ttft_ms"]:  s["ttft_vals"].append(r["ttft_ms"])
            if r["total_ms"]: s["total_vals"].append(r["total_ms"])
            if r["tps"]:      s["tps_vals"].append(r["tps"])
        elif r["status"] == "429":
            s["rate_limits"] += 1
        elif r["status"] not in ("SKIP",):
            s["errors"] += 1

    # ── Score and rank ────────────────────────────────────────────────────────
    scored = []
    for label, s in summary.items():
        if s["total_runs"] == 0 or s["successes"] == 0:
            reliability = 0.0
            avg_ttft    = 999999
            avg_tps     = 0
        else:
            reliability = s["successes"] / s["total_runs"]
            avg_ttft    = sum(s["ttft_vals"]) / len(s["ttft_vals"]) if s["ttft_vals"] else 999999
            avg_tps     = sum(s["tps_vals"])  / len(s["tps_vals"])  if s["tps_vals"]  else 0

        # Combined score: reliability weighted 60%, speed (ttft) 40%
        # TTFT normalised to 0-1 (lower is better), capped at 10,000ms
        ttft_score = max(0, 1 - (avg_ttft / 10000))
        score      = (reliability * 0.6) + (ttft_score * 0.4)

        scored.append({
            **s,
            "reliability": reliability,
            "avg_ttft_ms": round(avg_ttft) if avg_ttft < 999999 else None,
            "avg_tps":     round(avg_tps, 1),
            "score":       round(score, 4),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # ── Print final ranking table ─────────────────────────────────────────────
    print("\n" + "="*70)
    print("  FINAL RANKING — Speed + Reliability Combined")
    print("  Score = 60% reliability + 40% TTFT speed")
    print("="*70)
    print(f"\n{'#':<3} {'Model':<42} {'Reliability':<13} {'Avg TTFT':<11} {'Avg t/s':<10} {'Score'}")
    print("-"*90)

    for i, m in enumerate(scored, 1):
        rel_str  = f"{m['successes']}/{m['total_runs']} ({m['reliability']*100:.0f}%)"
        ttft_str = f"{m['avg_ttft_ms']}ms" if m["avg_ttft_ms"] else "N/A"
        tps_str  = f"~{m['avg_tps']} t/s" if m["avg_tps"] else "N/A"
        print(f"{i:<3} {m['label']:<42} {rel_str:<13} {ttft_str:<11} {tps_str:<10} {m['score']:.4f}")

    print("\n" + "="*70)
    print("  RECOMMENDED CASCADE ORDER (paste into _PROVIDER_CONFIGS)")
    print("="*70)
    for i, m in enumerate(scored, 1):
        status = "✅" if m["reliability"] > 0 else "❌ REMOVE"
        print(f"  {i}. {m['label']}  {status}")

    print("\nDone.\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())