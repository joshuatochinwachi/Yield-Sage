# YieldSage API Documentation

---

## 1. Global Specifications

### Authentication
Certain endpoints require authentication using a Supabase-issued JSON Web Token (JWT).
To call protected routes, append the token in the request headers as a Bearer token:
```http
Authorization: Bearer <your_supabase_jwt_token>
```
*   **Public Routes:** Free access, no token required.
*   **Protected Routes:** Denied with `401 Unauthorized` if a valid token is missing or expired.

### Headers
Every request should declare:
```http
Content-Type: application/json
Accept: application/json
```

### Standard Error Response Format
All errors return a uniform schema matching FastAPI's default:
```json
{
  "detail": "Error explanation string or structured object"
}
```

---

## 2. API Endpoints Reference

### 2.1 Overview Statistics (`GET /api/stats/overview`)
*   **Access:** Public
*   **Purpose:** Fetches headline summary stats for the dashboard counters.
*   **Parameters:** None
*   **Response Format:**
    ```json
    {
      "protocols_tracked": 12,
      "pools_tracked": 152,
      "total_tvl": 45678239.12,
      "average_apy": 14.28,
      "median_apy": 8.52,
      "last_data_refresh": "2026-06-06T08:00:00.000Z"
    }
    ```
*   **Example Request:**
    ```bash
    curl -X GET "https://api.yieldsageai.xyz/api/stats/overview"
    ```

---

### 2.2 Yield Opportunities Leaderboard (`GET /api/yields/leaderboard`)
*   **Access:** Public
*   **Purpose:** Returns a paginated list of active yield pools on Mantle, sorted and filtered.
*   **Query Parameters:**
    | Parameter | Type | Required | Default | Description |
    |---|---|---|---|---|
    | `page` | integer | No | `1` | Page number for pagination (min: 1) |
    | `page_size` | integer | No | `20` | Results per page (min: 1, max: 100) |
    | `search` | string | No | `null` | Filter by protocol name, pool name, or pool address |
    | `risk_tag` | string | No | `null` | Filter by risk profile: `stable` \| `moderate` \| `aggressive` |
    | `min_tvl` | number | No | `null` | Minimum Total Value Locked in USD |
    | `min_apy` | number | No | `null` | Minimum total APY percentage |
    | `sort_by` | string | No | `apy` | Column to sort by: `apy` \| `tvl_usd` \| `base_apy` \| `reward_apy` |
    | `sort_dir` | string | No | `desc` | Sort direction: `asc` \| `desc` |
*   **Response Format:**
    ```json
    {
      "data": [
        {
          "id": "2d9a3b6f-87e2-4c28-98e9-410a56fe73bc",
          "protocol_id": "8a32d1be-94e8-4c12-87ff-46bfa3bc58ee",
          "asset": "USDe-WMNT",
          "apy": 18.42,
          "base_apy": 6.84,
          "reward_apy": 11.58,
          "tvl_usd": 4200000.00,
          "reward_tokens": "MNT",
          "apy_1d": 0.23,
          "apy_7d": -0.11,
          "apy_30d": 5.80,
          "fetched_at": "2026-06-06T08:00:00Z",
          "protocol": {
            "id": "8a32d1be-94e8-4c12-87ff-46bfa3bc58ee",
            "slug": "merchant-moe-usde-wmnt-0d16c4",
            "name": "Merchant Moe",
            "pool_name": "USDe-WMNT",
            "pool_address": "0x5d54d430d1fd9425976147318e6080479bffc16d",
            "risk_tag": "moderate",
            "image_url": "https://yieldsage.xyz/logos/moe.png",
            "app_link": "https://app.merchantmoe.xyz"
          }
        }
      ],
      "total": 152,
      "page": 1,
      "page_size": 20,
      "has_more": true
    }
    ```
*   **Example Request:**
    ```bash
    curl -X GET "https://api.yieldsageai.xyz/api/yields/leaderboard?risk_tag=moderate&min_tvl=100000&sort_by=apy"
    ```

---

### 2.3 APY Historical Timeseries (`GET /api/yields/history/{protocol_id}`)
*   **Access:** Public
*   **Purpose:** Fetches historical APY data points for chart rendering.
*   **Path Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `protocol_id` | string (UUID) | Yes | The database ID of the protocol/pool |
*   **Query Parameters:**
    | Parameter | Type | Required | Default | Description |
    |---|---|---|---|---|
    | `days` | integer | No | `30` | Number of days of historical data to retrieve (max: 90) |
*   **Response Format:**
    ```json
    {
      "protocol_id": "8a32d1be-94e8-4c12-87ff-46bfa3bc58ee",
      "data_points": [
        {
          "apy": 18.42,
          "base_apy": 6.84,
          "reward_apy": 11.58,
          "tvl_usd": 4200000.00,
          "fetched_at": "2026-06-06T08:00:00Z"
        },
        {
          "apy": 18.25,
          "base_apy": 6.75,
          "reward_apy": 11.50,
          "tvl_usd": 4180000.00,
          "fetched_at": "2026-06-06T07:00:00Z"
        }
      ]
    }
    ```

---

### 2.4 Watchlist Yield Data (`GET /api/yields/watchlist`)
*   **Access:** Public
*   **Purpose:** Returns the latest yield snapshot details for a customized list of protocol IDs.
*   **Query Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `ids` | string | Yes | Comma-separated list of protocol UUIDs (e.g. `uuid1,uuid2`) |
*   **Response Format:**
    ```json
    {
      "data": [
        {
          "protocol_id": "8a32d1be-94e8-4c12-87ff-46bfa3bc58ee",
          "name": "Merchant Moe",
          "pool_name": "USDe-WMNT",
          "apy": 18.42,
          "tvl_usd": 4200000.00,
          "risk_tag": "moderate"
        }
      ]
    }
    ```

---

### 2.5 Latest AI Recommendations (`GET /api/recommendations/latest`)
*   **Access:** Public
*   **Purpose:** Returns the current active top recommendations for all risk tiers (or a filtered tier).
*   **Query Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `risk_tag` | string | No | Optional risk filter: `stable` \| `moderate` \| `aggressive` |
*   **Response Format:**
    ```json
    {
      "data": {
        "stable": {
          "id": "e9a6bc8d-327c-482d-88b9-112dfdbe39ab",
          "risk_tag": "stable",
          "rank": 1,
          "apy_at_time": 6.12,
          "ai_reasoning": "Agni USDC/USDT is the safest path to yield on Mantle...",
          "ai_model": "llama-3.3-70b",
          "on_chain_tx_hash": "0x5d082a6f...",
          "on_chain_logged_at": "2026-06-06T08:02:12Z",
          "recommendation_hash": "b2f8a91...",
          "created_at": "2026-06-06T08:01:00Z",
          "explorer_url": "https://mantlescan.xyz/tx/0x5d082a6f...",
          "protocols": {
            "id": "112e87ab...",
            "slug": "agni-usdc-usdt",
            "name": "Agni Finance",
            "pool_name": "USDC-USDT",
            "pool_address": "0x12a...",
            "image_url": "https://...",
            "app_link": "https://..."
          }
        },
        "moderate": null,
        "aggressive": null
      },
      "timestamp": "2026-06-06T08:05:00Z"
    }
    ```

---

### 2.6 Verify Proof Payload (`GET /api/recommendations/verify/{tx_hash}`)
*   **Access:** Public
*   **Purpose:** Retrieves a recommendation and reconstructs its canonical payload client-side verification.
*   **Path Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `tx_hash` | string | Yes | The Mantle transaction hash containing the recommendation memo |
*   **Response Format:**
    ```json
    {
      "data": {
        "id": "e9a6bc8d-327c-482d-88b9-112dfdbe39ab",
        "risk_tag": "stable",
        "rank": 1,
        "apy_at_time": 6.12,
        "recommendation_hash": "7a3b4e...",
        "on_chain_tx_hash": "0x5d082a6f...",
        "protocols": {
          "name": "Agni Finance",
          "pool_name": "USDC-USDT",
          "pool_address": "0x12a..."
        }
      },
      "canonical_payload": "{\"ai_model\":\"llama-3.3-70b\",\"ai_reasoning\":\"...\",\"apy_at_time\":\"6.1200\",\"chain\":\"mantle\",\"chain_id\":5000,\"pool_address\":\"0x12a...\",\"pool_name\":\"USDC-USDT\",\"protocol_name\":\"Agni Finance\",\"rank\":1,\"risk_tag\":\"stable\",\"source\":\"dune_query_7595582\",\"scored_at\":\"2026-06-06T08:01:00Z\",\"tvl_usd\":\"1200500.00\",\"version\":\"1.0\"}"
    }
    ```

---

### 2.7 Fetch Paper Trades (`GET /api/user/trades`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Fetches the active and closed simulated investments of the logged-in user, enriched with live yields and daily/annual accrued profits.
*   **Query Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `status` | string | No | Filter by status: `active` \| `closed` |
*   **Response Format:**
    ```json
    {
      "data": [
        {
          "id": "5f6e3c28-9f3a-442b-980b-41bc0a9f5d16",
          "user_id": "c1a2d3e4-5b6f-7a8b-9c0d-1e2f3a4b5c6d",
          "protocol_id": "8a32d1be-94e8-4c12-87ff-46bfa3bc58ee",
          "simulated_investment_usd": 1000.00,
          "entry_apy": 18.42,
          "status": "active",
          "created_at": "2026-06-05T12:00:00Z",
          "closed_at": null,
          "protocols": {
            "id": "8a32d1be-94e8-4c12-87ff-46bfa3bc58ee",
            "slug": "merchant-moe-usde-wmnt-0d16c4",
            "name": "Merchant Moe",
            "pool_name": "USDe-WMNT",
            "pool_address": "0x5d54d430d1fd9425976147318e6080479bffc16d",
            "risk_tag": "moderate"
          },
          "live": {
            "current_apy": 18.25,
            "apy_delta": -0.17,
            "estimated_daily_yield_usd": 0.50,
            "estimated_annual_yield_usd": 182.50,
            "performance_status": "stable"
          }
        }
      ],
      "count": 1
    }
    ```

---

### 2.8 Open Paper Trade (`POST /api/user/trades`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Opens a new simulated position.
*   **Request Schema:**
    ```json
    {
      "protocol_id": "8a32d1be-94e8-4c12-87ff-46bfa3bc58ee",
      "simulated_investment_usd": 5000.00,
      "entry_apy": 18.42
    }
    ```
*   **Response Format:**
    ```json
    {
      "data": {
        "id": "77fbe61c...",
        "user_id": "c1a2d3e4...",
        "protocol_id": "8a32d1be...",
        "simulated_investment_usd": 5000.00,
        "entry_apy": 18.42,
        "status": "active",
        "created_at": "2026-06-06T09:00:00Z",
        "protocol": {
          "id": "8a32d1be...",
          "name": "Merchant Moe",
          "pool_name": "USDe-WMNT",
          "risk_tag": "moderate"
        }
      },
      "message": "Paper trade opened: $5,000 in Merchant Moe at 18.42% APY."
    }
    ```

---

### 2.9 Close Paper Trade (`PUT /api/user/trades/{trade_id}/close`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Closes an active simulated trade, freezing profits/yields accrued.
*   **Path Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `trade_id` | string (UUID) | Yes | The unique ID of the paper trade to close |
*   **Response Format:**
    ```json
    {
      "data": {
        "id": "5f6e3c28-9f3a-442b-980b-41bc0a9f5d16",
        "status": "closed",
        "closed_at": "2026-06-06T09:02:15Z"
      },
      "message": "Trade closed successfully."
    }
    ```

---

## 3. Implementation Code Example

To access a protected route from your custom frontend or client, fetch a session from Supabase, then make the HTTP request using the access token:

```typescript
import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient('SUPABASE_URL', 'SUPABASE_ANON_KEY');

async function fetchMySimulatedPositions() {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    console.error("User not logged in!");
    return;
  }

  try {
    const response = await axios.get('https://api.yieldsageai.xyz/api/user/trades', {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        'Content-Type': 'application/json'
      }
    });
    console.log("My Simulated Trades:", response.data);
  } catch (error) {
    console.error("API Call Failed:", error.response?.data || error.message);
  }
}
```
