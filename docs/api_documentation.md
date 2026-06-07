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

### Router: Stats (`/api/stats`)

---

#### 2.1 Overview Statistics (`GET /api/stats/overview`)
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

### Router: Yields (`/api/yields`)

---

#### 2.2 Latest Yields (`GET /api/yields/latest`)
*   **Access:** Public
*   **Purpose:** Returns the most recent yield snapshot for every active protocol, ordered by APY descending.
*   **Query Parameters:**
    | Parameter | Type | Required | Default | Description |
    |---|---|---|---|---|
    | `risk_tag` | string | No | `null` | Filter by risk profile: `stable` \| `moderate` \| `aggressive` |
    | `limit` | integer | No | `50` | Maximum number of results to return (1–200) |
*   **Response Format:**
    ```json
    {
      "data": [
        {
          "id": "...",
          "protocol_id": "...",
          "apy": 18.42,
          "base_apy": 6.84,
          "reward_apy": 11.58,
          "tvl_usd": 4200000.00,
          "apy_1d": 0.23,
          "apy_7d": -0.11,
          "apy_30d": 5.80,
          "fetched_at": "2026-06-06T08:00:00Z",
          "protocol": {
            "id": "...",
            "slug": "merchant-moe-usde-wmnt-0d16c4",
            "name": "Merchant Moe",
            "pool_name": "USDe-WMNT",
            "pool_address": "0x5d54d430d1fd9425976147318e6080479bffc16d",
            "risk_tag": "moderate",
            "image_url": "https://...",
            "app_link": "https://..."
          }
        }
      ],
      "count": 50,
      "timestamp": "2026-06-06T08:05:00Z"
    }
    ```

---

#### 2.3 Yield Leaderboard (`GET /api/yields/leaderboard`)
*   **Access:** Public
*   **Purpose:** Returns a paginated leaderboard of all active yield pools on Mantle, ranked by TVL descending with filtering.
*   **Query Parameters:**
    | Parameter | Type | Required | Default | Description |
    |---|---|---|---|---|
    | `page` | integer | No | `1` | Page number for pagination (min: 1) |
    | `page_size` | integer | No | `20` | Results per page (min: 1, max: 500) |
    | `search` | string | No | `null` | Filter by protocol name, pool name, or asset |
    | `risk_tag` | string | No | `null` | Filter by risk profile: `stable` \| `moderate` \| `aggressive` |
    | `min_tvl` | number | No | `null` | Minimum Total Value Locked in USD |
    | `min_apy` | number | No | `null` | Minimum total APY percentage |
*   **Response Format:**
    ```json
    {
      "data": [
        {
          "rank": 1,
          "protocol_id": "...",
          "slug": "merchant-moe-usde-wmnt-0d16c4",
          "name": "Merchant Moe",
          "pool_name": "USDe-WMNT",
          "pool_address": "0x5d54...",
          "risk_tag": "moderate",
          "image_url": "https://...",
          "app_link": "https://...",
          "apy": 18.42,
          "base_apy": 6.84,
          "reward_apy": 11.58,
          "reward_tokens": "MNT",
          "apy_1d": 0.23,
          "apy_7d": -0.11,
          "apy_30d": 5.80,
          "tvl_usd": 4200000.00,
          "asset": "USDe-WMNT",
          "fetched_at": "2026-06-06T08:00:00Z",
          "protocol": { "..." }
        }
      ],
      "total": 152,
      "page": 1,
      "page_size": 20,
      "total_pages": 8
    }
    ```

---

#### 2.4 APY Historical Timeseries (`GET /api/yields/history/{slug}`)
*   **Access:** Public
*   **Purpose:** Fetches hourly APY snapshots for a specific protocol over the past N days (chart rendering).
*   **Path Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `slug` | string | Yes | The unique slug of the protocol/pool |
*   **Query Parameters:**
    | Parameter | Type | Required | Default | Description |
    |---|---|---|---|---|
    | `days` | integer | No | `30` | Number of days of historical data to retrieve (max: 90) |
*   **Response Format:**
    ```json
    {
      "protocol": {
        "id": "...",
        "slug": "merchant-moe-usde-wmnt-0d16c4",
        "name": "Merchant Moe",
        "pool_name": "USDe-WMNT",
        "pool_address": "0x5d54...",
        "risk_tag": "moderate"
      },
      "days": 30,
      "data": [
        {
          "apy": 18.25,
          "base_apy": 6.75,
          "reward_apy": 11.50,
          "tvl_usd": 4180000.00,
          "apy_7d": -0.11,
          "apy_30d": 5.80,
          "asset": "USDe-WMNT",
          "fetched_at": "2026-06-06T07:00:00Z"
        }
      ],
      "count": 720
    }
    ```

### Router: Protocols (`/api/protocols`)

---

#### 2.5 List Protocols (`GET /api/protocols`)
*   **Access:** Public
*   **Purpose:** Returns all active protocols, optionally filtered by risk tier. Each protocol includes its most recent APY snapshot inline.
*   **Query Parameters:**
    | Parameter | Type | Required | Default | Description |
    |---|---|---|---|---|
    | `risk_tag` | string | No | `null` | Filter by risk profile: `stable` \| `moderate` \| `aggressive` |
    | `include_inactive` | boolean | No | `false` | Include deactivated protocols |
*   **Response Format:**
    ```json
    {
      "data": [
        {
          "id": "...",
          "slug": "merchant-moe-usde-wmnt-0d16c4",
          "name": "Merchant Moe",
          "pool_name": "USDe-WMNT",
          "pool_address": "0x5d54...",
          "risk_tag": "moderate",
          "chain": "mantle",
          "is_active": true,
          "created_at": "2026-06-01T00:00:00Z",
          "latest_snapshot": {
            "protocol_id": "...",
            "apy": 18.42,
            "tvl_usd": 4200000.00,
            "apy_7d": -0.11,
            "fetched_at": "2026-06-06T08:00:00Z"
          }
        }
      ],
      "count": 12
    }
    ```

---

#### 2.6 Protocol Detail (`GET /api/protocols/{slug}`)
*   **Access:** Public
*   **Purpose:** Returns full detail for a single protocol: metadata, latest snapshot, historical sparkline data (last 30 snapshots), and latest AI recommendation.
*   **Path Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `slug` | string | Yes | The unique slug identifier of the protocol |
*   **Response Format:**
    ```json
    {
      "protocol": { "id": "...", "slug": "...", "name": "...", "..." },
      "latest_snapshot": { "apy": 18.42, "tvl_usd": 4200000.00, "..." },
      "history": [
        { "apy": 17.80, "tvl_usd": 4100000.00, "fetched_at": "2026-06-05T08:00:00Z" }
      ],
      "latest_recommendation": {
        "rank": 1,
        "risk_tag": "moderate",
        "apy_at_time": 18.42,
        "ai_reasoning": "...",
        "ai_model": "llama-3.3-70b",
        "on_chain_tx_hash": "0x5d082a6f...",
        "created_at": "2026-06-06T08:01:00Z"
      }
    }
    ```

### Router: Recommendations (`/api/recommendations`)

---

#### 2.7 Latest AI Recommendations (`GET /api/recommendations/latest`)
*   **Access:** Public
*   **Purpose:** Returns the most recent AI recommendation for each risk tier (stable / moderate / aggressive).
*   **Query Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `risk_tag` | string | No | Optional risk filter: `stable` \| `moderate` \| `aggressive` |
*   **Response Format:**
    ```json
    {
      "data": {
        "stable": {
          "id": "...",
          "risk_tag": "stable",
          "rank": 1,
          "apy_at_time": 6.12,
          "ai_reasoning": "...",
          "ai_model": "llama-3.3-70b",
          "on_chain_tx_hash": "0x5d082a6f...",
          "on_chain_logged_at": "2026-06-06T08:02:12Z",
          "recommendation_hash": "b2f8a91...",
          "created_at": "2026-06-06T08:01:00Z",
          "explorer_url": "https://mantlescan.xyz/tx/0x5d082a6f...",
          "protocols": {
            "id": "...",
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

#### 2.8 Recommendation History (`GET /api/recommendations/history`)
*   **Access:** Public
*   **Purpose:** Returns a paginated list of all historical recommendations with on-chain proof links.
*   **Query Parameters:**
    | Parameter | Type | Required | Default | Description |
    |---|---|---|---|---|
    | `page` | integer | No | `1` | Page number |
    | `page_size` | integer | No | `20` | Results per page (max: 100) |
    | `risk_tag` | string | No | `null` | Filter by risk tier |
*   **Response Format:**
    ```json
    {
      "data": [
        {
          "id": "...",
          "risk_tag": "moderate",
          "rank": 1,
          "apy_at_time": 18.42,
          "ai_reasoning": "...",
          "ai_model": "llama-3.3-70b",
          "on_chain_tx_hash": "0x82b4...",
          "recommendation_hash": "7a3b4e...",
          "created_at": "2026-06-06T08:01:00Z",
          "explorer_url": "https://mantlescan.xyz/tx/0x82b4...",
          "protocols": { "..." }
        }
      ],
      "total": 312,
      "page": 1,
      "page_size": 20,
      "has_more": true
    }
    ```

---

#### 2.9 Single Recommendation (`GET /api/recommendations/{rec_id}`)
*   **Access:** Public
*   **Purpose:** Fetches a single recommendation by its UUID.
*   **Path Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `rec_id` | string (UUID) | Yes | The database ID of the recommendation |
*   **Response Format:**
    ```json
    {
      "data": {
        "id": "...",
        "risk_tag": "stable",
        "rank": 1,
        "apy_at_time": 6.12,
        "ai_reasoning": "...",
        "ai_model": "llama-3.3-70b",
        "on_chain_tx_hash": "0x5d082a6f...",
        "recommendation_hash": "7a3b4e...",
        "explorer_url": "https://mantlescan.xyz/tx/0x5d082a6f...",
        "protocols": { "..." }
      }
    }
    ```

---

#### 2.10 Verify Proof Payload (`GET /api/recommendations/verify/{tx_hash}`)
*   **Access:** Public
*   **Purpose:** Retrieves a recommendation by its Mantle transaction hash and reconstructs its canonical payload for client-side verification. Uses case-insensitive matching and 0x-prefix fallback for robustness.
*   **Path Parameters:**
    | Parameter | Type | Required | Description |
    |---|---|---|---|
    | `tx_hash` | string | Yes | The Mantle transaction hash containing the recommendation memo |
*   **Response Format:**
    ```json
    {
      "data": {
        "id": "...",
        "risk_tag": "stable",
        "rank": 1,
        "apy_at_time": 6.12,
        "recommendation_hash": "7a3b4e...",
        "on_chain_tx_hash": "0x5d082a6f...",
        "explorer_url": "https://mantlescan.xyz/tx/0x5d082a6f...",
        "protocols": {
          "name": "Agni Finance",
          "pool_name": "USDC-USDT",
          "pool_address": "0x12a..."
        }
      },
      "canonical_payload": "{\"ai_model\":\"llama-3.3-70b\",\"ai_reasoning\":\"...\",\"apy_at_time\":\"6.1200\",\"chain\":\"mantle\",\"chain_id\":5000,\"pool_address\":\"0x12a...\",\"pool_name\":\"USDC-USDT\",\"protocol_name\":\"Agni Finance\",\"rank\":1,\"risk_tag\":\"stable\",\"source\":\"dune_query_7595582\",\"scored_at\":\"2026-06-06T08:01:00Z\",\"tvl_usd\":\"1200500.00\",\"version\":\"1.0\"}"
    }
    ```

### Router: User (`/api/user`) — Protected

---

#### 2.11 Get User Profile (`GET /api/user/profile`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Returns the authenticated user's profile, enriched with alert preference settings.
*   **Response Format:**
    ```json
    {
      "data": {
        "id": "c1a2d3e4-...",
        "email": "user@example.com",
        "full_name": "Alice",
        "telegram_chat_id": 1234567890,
        "risk_preference": "stable,moderate,aggressive",
        "created_at": "2026-06-01T00:00:00Z",
        "alert_preferences": {
          "is_active": true,
          "stable_apy_threshold": null,
          "moderate_apy_threshold": null,
          "aggressive_apy_threshold": null
        }
      }
    }
    ```

---

#### 2.12 Update User Profile (`PUT /api/user/profile`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Updates the user's display name and/or risk preference.
*   **Request Schema:**
    ```json
    {
      "full_name": "Alice Updated",
      "risk_preference": "stable,moderate"
    }
    ```
*   **Response Format:**
    ```json
    {
      "data": { "id": "...", "full_name": "Alice Updated", "risk_preference": "stable,moderate", "..." },
      "message": "Profile updated successfully."
    }
    ```

---

#### 2.13 Connect Telegram (`POST /api/user/telegram/connect`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Links a Telegram `chat_id` to the authenticated user's account for hourly alerts. Automatically provisions an `alert_preferences` row if missing.
*   **Request Schema:**
    ```json
    {
      "telegram_chat_id": 1234567890
    }
    ```
*   **Response Format:**
    ```json
    {
      "message": "Telegram account linked successfully.",
      "telegram_chat_id": 1234567890
    }
    ```
*   **Error Responses:**
    - `409 Conflict` — The Telegram account is already linked to a different user.

---

#### 2.14 Get Alert Preferences (`GET /api/user/alerts`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Returns the user's alert preference settings (thresholds and active/inactive toggle).
*   **Response Format:**
    ```json
    {
      "data": {
        "user_id": "c1a2d3e4-...",
        "is_active": true,
        "stable_apy_threshold": null,
        "moderate_apy_threshold": null,
        "aggressive_apy_threshold": null
      }
    }
    ```

---

#### 2.15 Update Alert Preferences (`PUT /api/user/alerts`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Updates alert thresholds and the active/inactive toggle. Performs an upsert — creates the row if it doesn't exist.
*   **Request Schema:**
    ```json
    {
      "is_active": true,
      "stable_apy_threshold": 5.0,
      "moderate_apy_threshold": 10.0,
      "aggressive_apy_threshold": 15.0
    }
    ```
*   **Response Format:**
    ```json
    {
      "data": { "..." },
      "message": "Alert preferences updated."
    }
    ```

---

#### 2.16 User Activity Log (`GET /api/user/activity`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Returns recent Telegram messages sent to this user (hourly alerts + query responses).
*   **Query Parameters:**
    | Parameter | Type | Required | Default | Description |
    |---|---|---|---|---|
    | `limit` | integer | No | `20` | Maximum number of messages to return |
*   **Response Format:**
    ```json
    {
      "data": [
        {
          "id": "...",
          "message_type": "daily_push",
          "content": "Your Merchant Moe position yielded...",
          "status": "sent",
          "sent_at": "2026-06-06T08:05:00Z",
          "error_message": null
        }
      ],
      "count": 15
    }
    ```

### Router: Paper Trades (`/api/paper-trades`) — Protected

---

#### 2.17 List Paper Trades (`GET /api/paper-trades`)
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
          "id": "5f6e3c28-...",
          "user_id": "c1a2d3e4-...",
          "protocol_id": "8a32d1be-...",
          "simulated_investment_usd": 1000.00,
          "entry_apy": 18.42,
          "status": "active",
          "created_at": "2026-06-05T12:00:00Z",
          "closed_at": null,
          "protocols": {
            "id": "8a32d1be-...",
            "name": "Merchant Moe",
            "pool_name": "USDe-WMNT",
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

#### 2.18 Open Paper Trade (`POST /api/paper-trades`)
*   **Access:** Protected (Supabase JWT Required)
*   **Purpose:** Opens a new simulated position.
*   **Request Schema:**
    ```json
    {
      "protocol_id": "8a32d1be-...",
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

#### 2.19 Close Paper Trade (`PUT /api/paper-trades/{trade_id}/close`)
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
        "id": "5f6e3c28-...",
        "status": "closed",
        "closed_at": "2026-06-06T09:02:15Z"
      },
      "message": "Trade closed successfully."
    }
    ```

### Health & System

---

#### 2.20 Service Identity (`GET /`)
*   **Access:** Public
*   **Response Format:**
    ```json
    {
      "service": "YieldSage API",
      "status": "running",
      "version": "1.0.0",
      "docs": "/docs",
      "timestamp": "2026-06-06T08:00:00Z"
    }
    ```

---

#### 2.21 Health Check (`GET /health`)
*   **Access:** Public
*   **Purpose:** Returns the health status of the scheduler and Telegram bot thread. Used by Railway for healthcheck probes.
*   **Response Format:**
    ```json
    {
      "status": "healthy",
      "scheduler_running": true,
      "bot_alive": true,
      "timestamp": "2026-06-06T08:00:00Z"
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
    const response = await axios.get('https://api.yieldsageai.xyz/api/paper-trades', {
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

