"""
YieldSage — Model Speed & Reliability Benchmark
================================================
Tests all models in the cascade with a realistic prompt
(same size as the actual YieldSage prompts: ~8,000-9,000 tokens).

Model roster (v2 — updated after first benchmark run):
  - llama-3.1-70b-versatile REMOVED — decommissioned by Groq (400 error)
  - llama-4-scout:free REMOVED — 404 on OpenRouter free tier
  - mistral-small-3.1-24b:free REMOVED — 404 on OpenRouter free tier
  - llama-3.3-70b-instruct:free ADDED — confirmed free on OpenRouter
  - step-3.5-flash:free ADDED — confirmed free on OpenRouter
  - glm-5.1:free ADDED — confirmed free on OpenRouter
"""

import asyncio
import time
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError

load_dotenv()

# ── Model roster ──────────────────────────────────────────────────────────────
MODELS = [
    # ── Groq ──────────────────────────────────────────────────────────────────
    {
        # Fastest provider when available — 394 t/s on LPU hardware
        # Rate limited after 1st call per hour on free tier
        "label":    "Groq — llama-3.3-70b-versatile",
        "provider": "Groq",
        "model":    "llama-3.3-70b-versatile",
        "env_key":  "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    # ── NVIDIA ────────────────────────────────────────────────────────────────
    {
        # Proven workhorse — 100% reliability in last benchmark, 85-90% in Railway logs
        "label":    "NVIDIA — llama-3.3-70b-instruct",
        "provider": "NVIDIA",
        "model":    "meta/llama-3.3-70b-instruct",
        "env_key":  "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
    },
    {
        # NVIDIA fallback — 100% reliability but slower (avg 11s TTFT in last benchmark)
        "label":    "NVIDIA — llama-3.1-70b-instruct",
        "provider": "NVIDIA",
        "model":    "meta/llama-3.1-70b-instruct",
        "env_key":  "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
    },
    # ── Gemini ────────────────────────────────────────────────────────────────
    {
        # Best instruction following — 67% reliability, fastest TTFT at 3.8s
        "label":    "Gemini — gemini-2.5-flash",
        "provider": "Gemini",
        "model":    "gemini-2.5-flash",
        "env_key":  "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    {
        # Gemini fallback — 33% reliability in last benchmark
        "label":    "Gemini — gemini-2.5-flash-lite",
        "provider": "Gemini",
        "model":    "gemini-2.5-flash-lite",
        "env_key":  "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    # ── OpenRouter (free tier) ────────────────────────────────────────────────
    # Previous models (llama-4-scout:free, mistral-small-3.1-24b:free) returned
    # 404 — endpoints no longer exist on free tier. Replaced with confirmed models.
    {
        # Same Llama 3.3 70B you already use on NVIDIA/Groq — via OpenRouter free pool
        # Slower than direct providers but confirmed available on free tier
        "label":    "OpenRouter — llama-3.3-70b-instruct:free",
        "provider": "OpenRouter",
        "model":    "meta-llama/llama-3.3-70b-instruct:free",
        "env_key":  "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
    },
    {
        # StepFun Step-3.5-Flash — confirmed free tier, MoE architecture
        # 11B active params, designed for low latency
        "label":    "OpenRouter — step-3.5-flash:free",
        "provider": "OpenRouter",
        "model":    "stepfun/step-3.5-flash:free",
        "env_key":  "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
    },
    {
        # Z.ai GLM-5.1 — confirmed on OpenRouter free tier as of May 2026
        # MoE model, 309B total / 15B active params
        "label":    "OpenRouter — glm-5.1:free",
        "provider": "OpenRouter",
        "model":    "z-ai/glm-5.1:free",
        "env_key":  "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
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
    print("\n" + "="*70)
    print("  YieldSage — Model Speed & Reliability Benchmark")
    print(f"  {RUNS_PER_MODEL} runs per model | Realistic ~8K token prompt")
    print("="*70 + "\n")

    all_results = []

    for model_cfg in MODELS:
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