# YieldSage API Reference

Base URL: `https://api.yieldsageai.xyz`

No authentication is required for read-only endpoints. All responses are JSON.

---

## GET /api/stats/overview

Returns aggregate statistics across all tracked Mantle DeFi protocols.

### Response Fields

| Field | Type | Description |
|---|---|---|
| `total_tvl_usd` | number | Combined TVL across all active pools in USD |
| `average_apy` | number | Mean APY across all active pool snapshots |
| `median_apy` | number | Median APY across all active pool snapshots |
| `total_protocols` | integer | Number of unique protocol names tracked |
| `total_pools` | integer | Total number of active pool entries |

### Example Response
```json
{
  "total_tvl_usd": 42800000,
  "average_apy": 14.72,
  "median_apy": 9.45,
  "total_protocols": 8,
  "total_pools": 34
}
```

---

## GET /api/yields/latest

Returns the most recent snapshot for every active pool.

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `risk_tag` | string | Filter by `stable`, `moderate`, or `aggressive` |
| `search` | string | Search by protocol name or pool asset name |

### Response Fields (per pool)

| Field | Type | Description |
|---|---|---|
| `protocol_name` | string | Protocol display name (e.g. "Agni Finance") |
| `pool_name` | string | Pool identifier (e.g. "USDC/USDT") |
| `pool_address` | string | On-chain pool contract address |
| `risk_tag` | string | `stable` / `moderate` / `aggressive` |
| `apy` | number | Total APY as a percentage |
| `base_apy` | number | Base (fee) APY component |
| `reward_apy` | number | Reward token APY component |
| `tvl_usd` | number | Total Value Locked in USD |
| `reward_tokens` | string | Reward token name(s) |
| `apy_1d` | number | APY 1 day ago (for trend) |
| `apy_7d` | number | APY 7 days ago (for trend) |
| `apy_30d` | number | APY 30 days ago (for trend) |
| `fetched_at` | ISO8601 | Timestamp of this snapshot |
| `app_link` | string | Direct link to the pool on the protocol's UI |

---

## GET /api/yields/leaderboard

Returns pools sorted by APY descending with filtering support.

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `risk_tag` | string | Filter by `stable`, `moderate`, or `aggressive` |
| `min_tvl` | number | Minimum TVL in USD |
| `min_apy` | number | Minimum APY threshold |
| `search` | string | Protocol or asset name search |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Results per page (default: 20) |

---

## GET /api/recommendations/latest

Returns the most recent AI-generated ranked picks per risk tier.

### Response Fields (per recommendation)

| Field | Type | Description |
|---|---|---|
| `rank` | integer | Rank within this risk tier (1 = top pick) |
| `protocol_name` | string | Protocol name |
| `pool_name` | string | Pool name |
| `risk_tag` | string | Risk tier |
| `apy_at_time` | number | APY at time recommendation was generated |
| `ai_reasoning` | string | Plain-English AI explanation (verbatim) |
| `ai_model` | string | LLM model that generated this recommendation |
| `on_chain_tx_hash` | string | Mantle TX hash of the SHA-256 commitment (null if pending) |
| `on_chain_logged_at` | ISO8601 | When the TX was confirmed on Mantle |
| `created_at` | ISO8601 | When the recommendation was generated |

---

## GET /api/recommendations/verify/{tx_hash}

Verifies a YieldSage recommendation against its on-chain SHA-256 commitment.

### Path Parameters

| Parameter | Description |
|---|---|
| `tx_hash` | The Mantle transaction hash (from `on_chain_tx_hash` field) |

### Response Fields

| Field | Type | Description |
|---|---|---|
| `verified` | boolean | `true` if the payload hash matches the on-chain commitment |
| `match` | boolean | Alias for `verified` |
| `recommendation_hash` | string | The SHA-256 hash of the canonical recommendation payload |
| `payload` | object | The canonical recommendation JSON that was hashed |
| `mantle_tx` | string | Mantlescan URL: `https://mantlescan.xyz/tx/{tx_hash}` |

### Verification Logic

YieldSage computes: `SHA-256(JSON.stringify(canonical_payload))` where `canonical_payload` contains:
`{ timestamp, protocol_id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model }`

The hash is embedded as `yieldsage:<hex_hash>` in the `data` field of a 0-MNT self-transaction on Mantle.

---

## GET /api/recommendations/history

Returns the full historical log of all recommendations with their on-chain TX hashes.

### Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `risk_tag` | string | Filter by risk tier |
| `protocol` | string | Filter by protocol slug |
| `limit` | integer | Max results to return (default: 50) |
| `offset` | integer | Pagination offset |

---

## GET /api/protocols

Returns the full registry of tracked protocols.

### Response Fields (per protocol)

| Field | Type | Description |
|---|---|---|
| `slug` | string | URL-safe identifier |
| `name` | string | Display name |
| `pool_name` | string | Pool pair name |
| `pool_address` | string | On-chain contract address |
| `risk_tag` | string | Default risk classification |
| `chain` | string | Always `mantle` |
| `image_url` | string | Protocol logo URL |
| `app_link` | string | Protocol UI deep-link |
| `is_active` | boolean | Whether actively tracked |
