# Dune Fetcher Retry Architecture

This document explains the robust retry mechanism implemented in `agent/fetcher.py` to handle transient failures and rate limits when interacting with the Dune Analytics API.

## How It Works

The Dune fetcher uses a nested loop approach to ensure maximum resilience when pulling yield data.

1. **API Key Rotation**: The fetcher first checks all available API keys and selects one that has remaining execution credits.
2. **Outer Loop (Execution Trigger)**: It attempts to trigger the Dune query up to `max_retries` (currently 30) times.
3. **Inner Loop (Status Polling)**: Once execution successfully starts, it polls Dune every 15 seconds to check the status.
   - If the query succeeds (`QUERY_STATE_COMPLETED`), the loop terminates and results are fetched.
   - If the query fails (`QUERY_STATE_FAILED`), the system aborts the inner loop, waits 15 seconds, and triggers a brand new execution attempt (incrementing the outer loop counter).
   - If the polling request itself fails (network error), it just waits 15 seconds and tries polling again without losing the execution session.

## Architecture Flowchart

```mermaid
flowchart TD
    Start([Start Session]) --> SelectKey[Select Valid API Key]
    SelectKey --> InitAttempt[attempt = 1 to 30]
    
    InitAttempt --> TriggerExec[POST /execute]
    
    TriggerExec -- HTTP Error --> WaitTrigger[Wait 15s]
    WaitTrigger --> CheckAttempt1{attempt < 30?}
    CheckAttempt1 -- Yes --> InitAttempt
    CheckAttempt1 -- No --> Fail([Raise RuntimeError])
    
    TriggerExec -- Success --> Monitor[Start Monitor Loop]
    
    Monitor --> WaitPoll[Wait 15s]
    WaitPoll --> PollStatus[GET /status]
    
    PollStatus -- HTTP Error --> WaitPoll
    
    PollStatus -- Success --> StateCheck{Check State}
    
    StateCheck -- "QUERY_STATE_COMPLETED" --> FetchCSV[Fetch CSV Data]
    FetchCSV --> Ingest[Ingest to Supabase]
    Ingest --> End([End Session])
    
    StateCheck -- "QUERY_STATE_EXECUTING / PENDING" --> WaitPoll
    
    StateCheck -- "QUERY_STATE_FAILED" --> CheckAttempt2{attempt < 30?}
    
    CheckAttempt2 -- Yes --> WaitFail[Wait 15s]
    WaitFail --> InitAttempt
    
    CheckAttempt2 -- No --> Fail
```

## Why 30 Retries?

Increasing `max_retries` to 30 provides excellent resilience against Dune's unpredictable query drops. 

Because we wait 15 seconds between failures, 30 retries gives the system **at least 2.5 minutes** to recover from a complete Dune outage or persistent rate-limiting block before giving up and crashing the scheduled job. This ensures that transient network hiccups or temporary Dune database overloads do not result in missing a critical hourly yield snapshot.

---

## Comprehensive Fetcher Scenarios

The diagrams below illustrate every path `fetcher.py` can take when interacting with the Dune Analytics API, and what happens at each decision point.

### Scenario A: Happy Path (First Attempt Succeeds)

The most common case. Dune is healthy, the query executes on the first try.

```mermaid
sequenceDiagram
    participant F as fetcher.py
    participant K as API Key Pool
    participant D as Dune API
    participant DB as Supabase

    F->>K: select_valid_key()
    K-->>F: Key with credits remaining

    F->>D: POST /execute (Attempt 1/30)
    D-->>F: 200 OK, execution_id = "abc123"

    loop Poll every 15s
        F->>D: GET /execution/abc123/status
        D-->>F: QUERY_STATE_EXECUTING
    end

    F->>D: GET /execution/abc123/status
    D-->>F: QUERY_STATE_COMPLETED

    F->>D: GET /results/csv
    D-->>F: CSV payload (APY, TVL, Asset data)

    F->>DB: UPSERT protocols
    F->>DB: INSERT yield_snapshots
    F->>F: Rotate key index for next session
```

### Scenario B: Query Fails, Retry Succeeds

Dune accepts the execution but internally drops it (database overload, resource contention). The fetcher detects `QUERY_STATE_FAILED`, sleeps 15s, and re-triggers.

```mermaid
sequenceDiagram
    participant F as fetcher.py
    participant D as Dune API
    participant DB as Supabase

    F->>D: POST /execute (Attempt 1/30)
    D-->>F: 200 OK, execution_id = "abc123"

    F->>D: GET /execution/abc123/status
    D-->>F: QUERY_STATE_FAILED

    Note over F: Attempt 1 failed. Sleep 15s before retry.
    F->>F: asyncio.sleep(15)

    F->>D: POST /execute (Attempt 2/30)
    D-->>F: 200 OK, execution_id = "def456"

    F->>D: GET /execution/def456/status
    D-->>F: QUERY_STATE_COMPLETED

    F->>D: GET /results/csv
    D-->>F: CSV payload
    F->>DB: UPSERT protocols + INSERT snapshots
```

### Scenario C: Execution Trigger HTTP Error

Dune's `/execute` endpoint itself returns an HTTP error (e.g., 429 rate limit, 500 server error). The fetcher never gets an `execution_id`, so it sleeps 15s and retries the POST.

```mermaid
sequenceDiagram
    participant F as fetcher.py
    participant D as Dune API

    F->>D: POST /execute (Attempt 1/30)
    D-->>F: 429 Too Many Requests

    Note over F: Trigger failed. Sleep 15s.
    F->>F: asyncio.sleep(15)

    F->>D: POST /execute (Attempt 2/30)
    D-->>F: 200 OK, execution_id = "ghi789"

    loop Poll every 15s
        F->>D: GET /execution/ghi789/status
        D-->>F: QUERY_STATE_COMPLETED
    end

    F->>D: GET /results/csv
    D-->>F: CSV payload
```

### Scenario D: Network Error During Polling

The execution is running on Dune, but a transient network issue (packet loss, DNS timeout) causes the status check to fail. The fetcher does **not** abandon the execution — it keeps the same `execution_id` and retries the poll.

```mermaid
sequenceDiagram
    participant F as fetcher.py
    participant D as Dune API

    F->>D: POST /execute (Attempt 1/30)
    D-->>F: 200 OK, execution_id = "abc123"

    F->>D: GET /execution/abc123/status
    D--xF: httpx.ReadError (Network cut)

    Note over F: Status check failed (not query failure). Sleep 15s, keep execution_id.
    F->>F: asyncio.sleep(15)

    F->>D: GET /execution/abc123/status
    D-->>F: QUERY_STATE_COMPLETED

    F->>D: GET /results/csv
    D-->>F: CSV payload
```

### Scenario E: All 30 Attempts Exhausted

Dune is in a prolonged outage. Every single attempt over ~2.5 minutes fails. The fetcher gives up and raises a `RuntimeError`, which is caught by `scheduler.py` and logged to the `agent_errors` table.

```mermaid
sequenceDiagram
    participant F as fetcher.py
    participant D as Dune API
    participant S as scheduler.py

    loop Attempts 1 through 30
        F->>D: POST /execute
        D-->>F: QUERY_STATE_FAILED (or HTTP Error)
        F->>F: asyncio.sleep(15)
    end

    Note over F: All 30 attempts exhausted.
    F-->>S: raise RuntimeError
    S->>S: Log error to agent_errors table
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **15s sleep between retries** | Matches Dune's own recommended polling interval. Avoids triggering additional rate limits while still recovering quickly. |
| **30 max retries** | Provides ~2.5 min recovery window. Long enough to survive a Dune deploy or brief outage, short enough to not block the scheduler indefinitely. |
| **Separate handling for poll errors vs query failures** | A network blip during polling does NOT mean the query failed on Dune — the execution may still be running. So we keep the same `execution_id` and retry the poll. A `QUERY_STATE_FAILED` response means Dune explicitly killed the query, so we must start a fresh execution. |
| **Key rotation after success** | After a successful session, `fetcher.py` rotates to the next API key for the *next* hourly run. This distributes credit consumption evenly across all keys. |



