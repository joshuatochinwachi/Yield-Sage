---
name: mantle-yieldsage-research
version: 0.1.0
description: "Use when a Mantle DeFi task requires discovering, comparing, or auditing yield opportunities across Agni Finance, Merchant Moe, and mETH Protocol. Returns risk-adjusted APY rankings, TVL data, and cryptographically verifiable on-chain proof anchored on Mantle."
---

# Mantle YieldSage Research

## Overview

Research and rank live DeFi yield opportunities on the Mantle Network using the YieldSage intelligence API. This skill fetches hourly-updated APY and TVL snapshots from Agni Finance, Merchant Moe, and mETH Protocol, retrieves AI-generated risk-adjusted recommendations, and verifies each recommendation against its SHA-256 commitment anchored on the Mantle blockchain.

Use this skill when:
- A user or downstream agent needs to discover the best current yield pools on Mantle
- A risk-tier comparison across `stable`, `moderate`, or `aggressive` pools is needed
- On-chain proof of an AI recommendation must be independently verified before capital deployment
- Historical recommendation data is needed to evaluate YieldSage track record

## When Not to Use

- Use `mantle-defi-operator` when the task is execution-ready transaction building (swaps, LP adds)
- Use `mantle-risk-evaluator` when the task is only a preflight risk verdict for a specific address
- Use `mantle-address-registry-navigator` when the task is only address lookup or anti-phishing review

## API Endpoints

All data is sourced from the live YieldSage REST API at `https://api.yieldsageai.xyz`. No API key required for read endpoints.

| Endpoint | Method | Description |
|---|---|---|
| `/api/yields/latest` | GET | All active pool snapshots with APY, TVL, risk tag, trend data |
| `/api/yields/leaderboard` | GET | APY-ranked pools, filterable by `risk_tag`, `min_tvl`, `search` |
| `/api/recommendations/latest` | GET | Current AI-ranked picks per risk tier with reasoning |
| `/api/recommendations/history` | GET | Full historical recommendation log with on-chain TX hashes |
| `/api/recommendations/verify/{tx_hash}` | GET | Cryptographic SHA-256 verification against Mantle blockchain |
| `/api/stats/overview` | GET | Aggregate TVL, average APY, protocol and pool counts |
| `/api/protocols` | GET | Full protocol registry (Agni, Merchant Moe, mETH, etc.) |

## Workflow

### Mode 1: Yield Discovery (default)

Use when the user asks "what are the best yields on Mantle?" or similar exploratory intent.

1. Call `GET /api/stats/overview` and report aggregate TVL and pool count as context.
2. Call `GET /api/yields/leaderboard` with user's risk preference (`risk_tag=stable|moderate|aggressive`).
3. Sort results by `apy` descending. Present the top 5 pools with:
   - Protocol name and pool name
   - Current APY and TVL in USD
   - Risk tier badge (`stable` / `moderate` / `aggressive`)
   - 1D / 7D / 30D APY trend direction
4. If the user has not specified a risk tier, present results across all tiers grouped by risk.
5. Do NOT fabricate APY values. Report only what the API returns.

### Mode 2: AI Recommendation Review

Use when the user asks "what does YieldSage recommend?" or requests ranked AI picks.

1. Call `GET /api/recommendations/latest`.
2. For each recommendation returned, present:
   - Rank, protocol, pool, APY at time of recommendation
   - AI reasoning (verbatim from `ai_reasoning` field — do not paraphrase)
   - Risk tier
   - On-chain TX hash and Mantlescan link: `https://mantlescan.xyz/tx/{on_chain_tx_hash}`
3. Always include the `on_chain_tx_hash` in the output so users can independently verify.
4. If `on_chain_tx_hash` is null, note the recommendation is pending on-chain commit.

### Mode 3: On-Chain Proof Verification

Use when the user provides a Mantle TX hash and asks to verify a YieldSage recommendation.

1. Call `GET /api/recommendations/verify/{tx_hash}`.
2. Report:
   - `verified: true` / `verified: false`
   - The recommendation payload (protocol, APY, reasoning, timestamp)
   - The computed SHA-256 hash
   - The Mantlescan link: `https://mantlescan.xyz/tx/{tx_hash}`
3. If verification fails, state "Hash mismatch — the recommendation payload may have been tampered."
4. Never claim verification without calling the endpoint. Do not compute hashes from memory.

### Mode 4: Historical Research

Use when the user wants to analyse the track record or history of recommendations.

1. Call `GET /api/recommendations/history`.
2. Present a chronological summary: date, recommended protocol, APY at time, on-chain TX.
3. Calculate directional accuracy only if current APY data is also fetched to compare.

## Guardrails

- **No address guessing**: Do not construct or guess Mantle contract addresses. Use protocol names only in research outputs. Defer address resolution to `mantle-address-registry-navigator`.
- **No fabricated data**: Every APY, TVL, and recommendation figure must come from a live API response in this session.
- **No execution**: This skill is research-only. Do not produce calldata, approval instructions, or transaction objects. Route execution intent to `mantle-defi-operator`.
- **Staleness warning**: YieldSage data refreshes hourly. If `fetched_at` on a snapshot is more than 2 hours old, include a staleness warning in the output.
- **Risk disclaimer**: Always append: *"YieldSage recommendations are for informational research purposes only and do not constitute financial advice."*

## Output Format

```
## YieldSage Yield Research — Mantle Network
Snapshot: {fetched_at}  |  Pools tracked: {total_pools}  |  Total TVL: ${total_tvl}

### Top {risk_tier} Yield Opportunities

| Rank | Protocol | Pool | APY | TVL | 7D Trend |
|------|----------|------|-----|-----|----------|
| 1    | ...      | ...  | ... | ... | ↑ / ↓ / → |

### AI Recommendation (Rank #{rank})
Pool: {pool_name} on {protocol_name}
APY: {apy_at_time}% | Risk: {risk_tag}
Reasoning: {ai_reasoning}
On-Chain Proof: https://mantlescan.xyz/tx/{on_chain_tx_hash}

---
*YieldSage recommendations are for informational research purposes only and do not constitute financial advice.*
```

## References

- `references/yieldsage-api-reference.md` — full endpoint schema and response field definitions
- `references/risk-tier-definitions.md` — how stable / moderate / aggressive pools are classified
- `references/on-chain-proof-guide.md` — how SHA-256 anchoring on Mantle works and how to verify
