# YieldSage System Architecture

**Version:** 1.2.0 — June 2026  
**Target Platform:** Mantle Network (Chain ID 5000)  
**Security Level:** Production-ready (RLS-enforced + Cryptographically audited)

This document describes the high-level system topology, decoupled service interactions, and data-flow sequences that govern the YieldSage runtime ecosystem.

---

## 1. High-Level Decoupled Architecture

YieldSage is built on a decoupled, asynchronous multi-tier architecture to guarantee high availability, resilient data ingestion, and trustless verification.

```mermaid
graph TB
    subgraph ClientLayer ["1. Client & User Layer"]
        NextJS["Next.js Web App\n(Vercel Edge Nodes)"]
        TGUser["Telegram Client\n(Mobile / Desktop)"]
    end

    subgraph GatewayLayer ["2. REST API Gateway"]
        FastAPI["FastAPI Web Service\n(Railway Web Container)"]
        JWTAuth["JWT Authentication\n(Supabase Auth)"]
        FastAPI <--> JWTAuth
    end

    subgraph DatabaseLayer ["3. Database Persistence"]
        DB[("Supabase PostgreSQL\n(RLS Policies Enforced)")]
    end

    subgraph AgentLayer ["4. Agent & Pipeline Layer"]
        Fetcher["Dune Ingestion Fetcher\n(agent/fetcher.py)"]
        Scorer["Scoring & Scoring Engine\n(agent/scorer.py)"]
        OnChainLogger["On-Chain Logger\n(agent/logger.py)"]
        TGBot["Telegram Bot Daemon\n(agent/bot.py)"]
        Scheduler["APScheduler Daemon\n(agent/scheduler.py)"]
    end

    subgraph ExternalServices ["5. Off-Chain & On-Chain Networks"]
        Dune["Dune Analytics API\n(Query #7595582)"]
        AICascade["LLM cascade Providers\n(Cerebras / SambaNova / Groq)"]
        Mantle["Mantle L2 Network\n(RPC Node Chain 5000)"]
    end

    %% Client Interactions
    NextJS <-->|HTTPS / JSON| FastAPI
    TGUser <-->|HTTPS / Webhook| TGBot
    TGBot <-->|Internal API Calls| FastAPI

    %% Gateway to Database
    FastAPI <-->|SQL Queries / Auth| DB

    %% Agent Interactions
    Scheduler -->|Every 60m| Fetcher
    Scheduler -->|Every 60m| Scorer
    Scheduler -->|Every 6h| OnChainLogger

    Fetcher -->|Dune API Key Pool| Dune
    Fetcher -->|Upsert Protocols & Snapshots| DB

    Scorer -->|Fetch Fresh Yields| DB
    Scorer -->|Execute Cascade Prompts| AICascade
    Scorer -->|Save AI Recommendations| DB

    OnChainLogger -->|Scan Missed Hashes| DB
    OnChainLogger -->|Send 0-MNT Transaction| Mantle
    
    DB <-->|Read / Write state| TGBot
```

---

## 2. Scheduled Pipeline Sequence Diagram

YieldSage operates on an automated 60-minute synchronization pipeline managed by `agent/scheduler.py`. This diagram shows the chronology of actions during an hourly run.

```mermaid
sequenceDiagram
    autonumber
    participant S as APScheduler
    participant F as DuneFetcher (fetcher.py)
    participant D as Dune Analytics API
    participant DB as Supabase PostgreSQL
    participant E as ScoringEngine (scorer.py)
    participant AI as AI Cascade (ai_service.py)
    participant L as OnChainLogger (logger.py)
    participant M as Mantle L2 Network

    %% Ingestion phase
    S->>F: Trigger Ingestion (Hourly Cron)
    activate F
    F->>F: Rotate API Key (Check Credits)
    F->>D: Execute Query 7595582
    activate D
    D-->>F: Return Yield CSV Dataset
    deactivate D
    F->>DB: Upsert Protocols & Snapshots (deduplicated)
    F-->>S: Ingestion Complete
    deactivate F

    %% Scoring phase
    S->>E: Trigger Scoring & Alerts
    activate E
    E->>DB: Query Latest Yield Snapshots
    activate DB
    DB-->>E: Return Live Snapshots
    deactivate DB
    E->>AI: Request Scoring & Reasoning Cascade
    activate AI
    AI->>AI: Evaluate APY Trends, TVL, and Asset Risks
    AI-->>E: Return AI Picks & Explanations
    deactivate AI
    E->>DB: Insert recommendations & user alerts
    E-->>S: Scoring Complete
    deactivate E

    %% On-Chain logging phase
    S->>L: Trigger On-Chain Logging
    activate L
    L->>DB: Fetch New Unlogged recommendations
    activate DB
    DB-->>L: Return Canonical recommendation Info
    deactivate DB
    L->>L: Serialize Canonical payload (Deterministic)
    L->>L: Compute SHA-256 Hash
    L->>M: Send 0-MNT self-transaction with memo: "yieldsage:<hash>"
    activate M
    M-->>L: Return Transaction Hash (tx_hash)
    deactivate M
    L->>DB: Update recommendation record (tx_hash, logged_at)
    L-->>S: Logging Complete
    deactivate L
```

---

## 3. Multi-LLM Cascade & Outage Recovery Flow

To ensure uninterrupted service, YieldSage routes queries through a priority queue of LLM providers. If a provider rate-limits or returns an error, the engine instantly falls back.

```mermaid
flowchart TD
    Start[User Query or Scorer Request] --> CheckInteractive{Query Type?}
    
    %% Interactive Routing
    CheckInteractive -->|Interactive Telegram| P1[Priority 1: Cerebras\nLlama-3.1-70B\nFastest Response]
    P1 -->|Success| Save[Return Response]
    P1 -->|Outage / Timeout| P2[Priority 2: SambaNova\nLlama-3.1-405B]
    P2 -->|Success| Save
    P2 -->|Outage / Timeout| P3[Priority 3: Groq\nLlama-3.3-70B]
    P3 -->|Success| Save
    P3 -->|Outage / Timeout| P4[Priority 4: NVIDIA NIM\nLlama-3-70B]
    P4 -->|Success| Save
    P4 -->|Outage / Timeout| P5[Priority 5: Google Gemini\nFlash-1.5\nFallback]
    P5 -->|Success| Save
    P5 -->|Failure| ErrorAlert[Return Error / Alert Ops]
    
    %% Background Routing (Reversed to save Cerebras credits for live users)
    CheckInteractive -->|Background Alerting| B1[Priority 1: SambaNova / Groq\nLarge Context Capacity]
    B1 -->|Success| Save
    B1 -->|Outage / Timeout| B2[Priority 2: NVIDIA NIM / Gemini]
    B2 -->|Success| Save
    B2 -->|Outage / Timeout| B3[Priority 3: Cerebras\nLast Fallback]
    B3 -->|Success| Save
    B3 -->|Failure| LogDbError[Log Fail to DB Queue]
```

---

## 4. On-Chain Commit & Recovery Lifecycle

If RPC latency or gas price fluctuations cause the initial Mantle transaction to fail, the system falls back to a 6-hourly recovery pipeline to ensure every recommendation is eventual-consistent on-chain.

```mermaid
stateDiagram-v2
    [*] --> RecommendationGenerated : Scorer completes run
    
    state In_Database {
        RecommendationGenerated --> HashComputed : Compute SHA-256 fingerprint
        HashComputed --> StoredInDB : Save recommendation with status (pending_log)
    }

    state Log_To_Mantle {
        StoredInDB --> BroadcastTx : Submit 0-MNT transaction to Mantle Network
        
        state ConfirmationCheck <<choice>>
        BroadcastTx --> ConfirmationCheck
        
        ConfirmationCheck --> VerifiedOnChain : Transaction confirmed (success)
        ConfirmationCheck --> FailToLog : RPC Timeout / Gas error (failure)
    }
    
    state Recovery_Scheduler {
        FailToLog --> SixHourCron : Waits in database with tx_hash = NULL
        SixHourCron --> FetchUnlogged : Recovery job scans for null tx_hash
        FetchUnlogged --> RecomputeHash : Reconstruct canonical payload & verify matches DB hash
        RecomputeHash --> ReBroadcastTx : Resubmit 0-MNT transaction
        
        state RecoveryCheck <<choice>>
        ReBroadcastTx --> RecoveryCheck
        
        RecoveryCheck --> VerifiedOnChain : Confirmed on Mantle (success)
        RecoveryCheck --> FailToLog : Retries exhausted (wait next 6h)
    }

    VerifiedOnChain --> [*] : Update DB with tx_hash & logged_at
```

---

## 5. Deployment & Security Architecture

### Network Configuration
*   **Vercel:** Hosts the Next.js frontend app. Traffic is routed through Vercel's global CDN Edge Nodes for maximum speed.
*   **Railway:** Runs the FastAPI web backend, Telegram listener daemon, and scheduled background workers within an isolated Docker private network.
*   **Supabase:** Secure PostgreSQL database layer. Port access is locked down; all user CRUD queries must validate against Row Level Security (RLS) rules matching the authenticated Supabase JWT.

### Key Management
*   **System Wallets:** Private keys required for signing Mantle transactions are injected directly into Railway environment variables. They are never committed to git or stored in public database columns.
*   **RPC Node Redundancy:** The Python `Web3` client contains automatic fallback routing. If `rpc.mantle.xyz` fails, it rotates requests to backup public RPC endpoints (e.g. `ankr.com/mantle`, `infura.io`) to ensure transactions are processed.
