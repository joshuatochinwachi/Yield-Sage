# YieldSage — Solana Migration Master Document

> **Version:** 2.0-SOLANA
> **Status:** Planning / Pre-Implementation
> **Replaces:** All prior Mantle-chain documentation
> **Date:** 2026-07-27
> **Author:** YieldSage Engineering

---

> **IMPORTANT MIGRATION NOTICE**
> This document supersedes all previous YieldSage documentation that references Mantle Network, Mantle RPC, MantleScan, Dune Analytics, `web3.py`, or MNT gas fees.
> The chain is **Solana**. The data source will be provided separately (not Dune). All references to Mantle and Dune in existing code must be treated as deprecated.

---

## Table of Contents

1. [Product Requirements Document (PRD)](#1-product-requirements-document-prd)
2. [Technical Requirements Document (TRD)](#2-technical-requirements-document-trd)
3. [UI/UX Design Specification](#3-uiux-design-specification)
4. [App Flow and User Journeys](#4-app-flow-and-user-journeys)
5. [Backend Architecture Schema](#5-backend-architecture-schema)
6. [Database Schema](#6-database-schema)
7. [Implementation Plan](#7-implementation-plan)
8. [Solana On-Chain Logging Procedure](#8-solana-on-chain-logging-procedure)
9. [Migration Delta — What Changes vs What Stays](#9-migration-delta--what-changes-vs-what-stays)
10. [Environment Variables Reference](#10-environment-variables-reference)
11. [Pre-Launch Checklist](#11-pre-launch-checklist)

---

---

# 1. Product Requirements Document (PRD)

## 1.1 Product Identity

**Product Name:** YieldSage
**Tagline:** *Your AI yield advisor on Solana — know where your crypto earns best, every single day.*
**Version:** 2.0 (Solana)
**Positioning:** An intelligent, always-on DeFi yield intelligence layer for Solana ecosystem participants — from curious newcomers to active liquidity providers.

---

## 1.2 The Problem

Solana's DeFi ecosystem is rich, fast-moving, and fragmented. At any given moment, there are dozens of protocols offering yield opportunities across lending, liquidity provision, staking, and restaking — each with their own dashboards, terminologies, and risk profiles. The average user:

- Lacks time to manually monitor 8+ Solana DeFi protocols daily
- Cannot objectively evaluate risk-adjusted returns across different yield types
- Has no cryptographically verifiable way to track who recommended what, and when
- Misses opportunity windows that open and close within hours

**Who feels this:** Solana-native users aged 22–45 who hold SOL, USDC, USDT, or liquid staking tokens (jitoSOL, mSOL, bSOL) and want to deploy capital intelligently without becoming full-time DeFi analysts.

---

## 1.3 The Solution

YieldSage v2 is a Solana-native yield intelligence platform that:

1. **Ingests** real-time yield data from Solana's top DeFi protocols via their native APIs and on-chain program reads
2. **Scores** every opportunity using an AI cascade (multi-model LLM pipeline) with risk-adjusted analysis
3. **Delivers** actionable recommendations in plain English via a web dashboard and Telegram bot
4. **Anchors** every recommendation permanently on Solana using an on-chain memo instruction — making every AI call cryptographically verifiable and tamper-proof
5. **Tracks** APY history and recommendation accuracy over time, building a public, verifiable track record

---

## 1.4 Target Users

**Primary User — The Active Solana Participant**
- Age 22–40, crypto-native, holds SOL and/or stablecoins on Solana
- Already uses 1–3 DeFi protocols but monitors them manually
- Active on Telegram daily
- Understands APY, TVL, and IL risk at a conceptual level
- Willing to pay for a high-signal daily briefing they trust

**Secondary User — The Solana Newcomer**
- Just bridged from Ethereum or bought SOL via Coinbase/Kraken
- Looking for their first DeFi yield opportunity
- Wants plain-English guidance, not raw protocol data
- Will become a primary user after their first successful deployment

**Tertiary User — The Protocol Analyst**
- Tracks Solana ecosystem TVL and APY trends professionally
- Uses YieldSage's public history page to validate AI recommendations
- Potential enterprise/API customer in v3

---

## 1.5 Core Features — v2 Must Have

### Data Intelligence Layer
- Automated data ingestion from Solana DeFi protocols (via a custom data pipeline — source TBD, NOT Dune)
- Support for at minimum 6 initial protocols spanning: lending, liquidity pools, liquid staking, and restaking
- Data refreshed on a configurable schedule (minimum hourly)
- Raw data stored in Supabase for audit and historical analysis
- Protocol metadata: name, category, pool name, on-chain program address, risk classification

### AI Scoring Engine
- Multi-provider LLM cascade (NVIDIA NIM primary -> Groq fallback -> Cerebras fallback -> cache)
- Risk-adjusted scoring across three tiers: **Stable** | **Moderate** | **Aggressive**
- Plain-English reasoning for every recommendation (2–4 sentences per pick)
- Top-3 picks per risk tier per scoring cycle
- Model used must be recorded per recommendation (for on-chain auditability)
- Fallback to last cached recommendation if all models unavailable

### On-Chain Verifiability (Solana Memo Program)
- Every recommendation batch anchored on Solana via the **SPL Memo Program** (Program ID: `MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr`)
- SHA-256 hash of the recommendation payload embedded in a Solana transaction memo
- Transaction signature stored in `recommendations.on_chain_tx_signature`
- Solana Explorer link rendered on every recommendation card and history row
- Retry logic: up to 3 attempts on RPC failure
- Recovery job: re-attempts any recommendation hashed but not yet logged on-chain

### Telegram Bot
- Daily push notification at 8:00 AM UTC with top picks per user's risk preference
- On-demand commands: `/best stable`, `/best moderate`, `/best aggressive`, `/top5`, `/protocol <name>`
- Account linking: `/connect <code>` links Telegram chat ID to Supabase user account
- All bot responses include Solana Explorer link to the on-chain proof
- Message delivery logged to `telegram_messages` table

### Web Dashboard
- Live yield leaderboard sortable by APY and risk tier
- Today's top recommendation card with AI reasoning and on-chain proof link
- 7-day and 30-day APY history charts per protocol (line chart, Recharts)
- Public recommendation history page — no auth required to browse
- Protocol deep-dive pages: APY trend, AI notes, risk breakdown, on-chain program address
- Mobile-responsive (bottom tab nav on mobile)

### Auth and User Management
- Supabase Auth: email + Google OAuth
- Onboarding: risk preference selection, optional Telegram connect
- Protected routes: unauthenticated users redirected to `/login`
- User settings: notification preferences, risk preference update, Telegram connection

---

## 1.6 Nice to Have (v3 Roadmap)

- Portfolio tracker: user inputs holdings, YieldSage shows current vs optimal yield allocation
- Wallet connect: personalised recommendations based on on-chain Solana wallet holdings
- Email digest as alternative/supplement to Telegram
- Risk scoring based on smart contract audit age, TVL stability, and exploit history
- Discord bot version
- Mobile app (React Native) wrapping the web dashboard
- Multi-chain expansion: Base, Arbitrum, Sui
- Referral programme (requires paid tier)
- API access tier for developers and institutional users

---

## 1.7 Out of Scope (v2)

- YieldSage does **NOT** execute trades or move funds on behalf of users
- YieldSage does **NOT** provide regulated financial advice — all recommendations carry a clear disclaimer
- YieldSage does **NOT** cover chains outside Solana in v2
- YieldSage does **NOT** support direct wallet connection or on-chain identity verification in v2
- YieldSage does **NOT** have a native mobile app in v2
- Stripe, paid tiers, and subscription billing are explicitly **deferred to v3**
- All v2 features are available to all registered users — no feature gating

---

## 1.8 User Stories

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-01 | Solana DeFi user | receive a daily Telegram message with the best yield right now | I don't monitor 8 protocols manually every morning |
| US-02 | Visitor | browse the live leaderboard without signing up | I can evaluate the product before committing |
| US-03 | Registered user | query `/best stable` at any time | I can act quickly when I have capital ready |
| US-04 | Sceptical visitor | click "Verify on Solana" on any recommendation | I can see cryptographic proof the AI said this before the fact |
| US-05 | New Solana user | receive plain-English explanations | I don't need to understand DeFi mechanics to benefit |
| US-06 | Power user | view the full recommendation history | I can evaluate the AI's track record before trusting it |
| US-07 | Developer / auditor | reconstruct the SHA-256 hash from DB data | I can independently verify on-chain logs match the recommendations |

---

## 1.9 Success Metrics

| Metric | Target |
|---|---|
| Telegram bot subscribers | 300+ within 2 weeks of launch |
| Dashboard unique visitors | 500+ in first month |
| Days of on-chain recommendation history | 30+ before any public announcement |
| Telegram query response time | < 3 seconds |
| Scheduler uptime | 99%+ (zero missed daily pushes) |
| On-chain logging success rate | > 95% of recommendations with a Solana tx signature |
| User retention (monthly active) | 60%+ of registered users active after 30 days |

---

---

# 2. Technical Requirements Document (TRD)

## 2.1 Technology Stack

### Frontend

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Framework | Next.js | 14 (App Router) | TypeScript strict mode |
| Styling | Tailwind CSS + custom CSS vars | 3.x | See design system section |
| Component library | shadcn/ui | latest | Customised to design system |
| Charts | Recharts | 2.x | APY trends, leaderboard sparklines |
| Auth client | @supabase/ssr | latest | SSR-safe Supabase session |
| Data fetching | @tanstack/react-query | 5.x | Caching, background refresh |
| Validation | zod | 3.x | Form and API response validation |
| Icons | lucide-react | latest | |
| Fonts | Google Fonts: Instrument Serif, DM Sans, DM Mono | — | Self-hosted via next/font |

### Backend

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Framework | FastAPI | 0.110+ | Async Python 3.11+ |
| Task scheduler | APScheduler | 3.x | Data fetch + scoring jobs |
| HTTP client | httpx | 0.27+ | Async HTTP for protocol APIs |
| Database ORM | Supabase Python client | 2.x | Direct Supabase client |
| AI SDK | openai (OpenAI-compatible) | 1.x | NVIDIA NIM + Groq via OpenAI compat API |
| Solana SDK | solders + solana-py | latest | Transaction building, RPC, Memo program |
| Telegram bot | python-telegram-bot | 20.x | Async, long-polling |
| Data validation | pydantic | 2.x | Request/response models |
| Environment | python-dotenv | 1.x | Local development |

### Solana-Specific Libraries

```
solders>=0.21.0          # Core Solana primitives: Keypair, Transaction, Instruction
solana>=0.35.0           # RPC client, PublicKey, SystemProgram
base58>=2.1.0            # Base58 encoding/decoding for keypair loading
```

### Database and Auth

| Service | Purpose |
|---|---|
| Supabase (PostgreSQL) | Primary database, auth, storage |
| Supabase Auth | Email + Google OAuth, JWT tokens |
| Supabase Row Level Security | Per-user data isolation |

### Hosting and Deployment

| Service | What runs there |
|---|---|
| Vercel | Next.js frontend |
| Railway | Python FastAPI + APScheduler + Telegram bot |
| Supabase | PostgreSQL database + Auth |

---

## 2.2 Solana Integration Architecture

### 2.2.1 RPC Providers

YieldSage will use a tiered RPC strategy for maximum reliability:

```
Primary:   Helius RPC (helius-rpc.com)                         -- high-rate, Solana-optimised
Secondary: QuickNode Solana endpoint                            -- fallback on rate limits  
Tertiary:  api.mainnet-beta.solana.com (public)                -- emergency fallback only
```

The public Solana RPC has aggressive rate limits (100 req/10s). Helius and QuickNode provide stable, production-grade access required for continuous operation.

### 2.2.2 On-Chain Logging — SPL Memo Program

The verifiability layer uses the **Solana SPL Memo Program** to anchor recommendation hashes on-chain.

**Program ID:** `MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr`

**Mechanism:**
1. Serialise recommendation payload to canonical JSON (sorted keys, no extra whitespace)
2. SHA-256 hash the JSON string
3. Build a Solana transaction with a single Memo instruction containing: `yieldsage:<sha256_hex>`
4. Sign with the YieldSage agent Solana keypair
5. Submit via `sendTransaction` to the Solana RPC
6. Store the returned transaction **signature** (base58 string, ~88 characters) in the database

**Cost:** Each Solana transaction costs approximately **0.000005 SOL** (5,000 lamports) in fees. At current prices, $5 worth of SOL covers over 10,000 transactions — effectively free for operational use.

### 2.2.3 Agent Wallet Management

The agent wallet is a dedicated Solana keypair used exclusively for on-chain memo logging. Rules:
- Never hold user funds
- Keep funded with a small SOL balance for transaction fees (~0.1 SOL is sufficient for months)
- Private key stored ONLY as an environment variable — never committed to git
- Key format: Solana keypairs stored as 64-byte base58 string or JSON array of 64 integers

### 2.2.4 Data Ingestion (Custom Pipeline)

> **Note:** The specific data source replacing Dune Analytics will be defined by the product team separately. The architecture below is data-source-agnostic — `fetcher.py` must implement a clear interface contract regardless of the upstream source.

The data pipeline must:
- Fetch APY, TVL, and pool metadata for each tracked Solana protocol
- Normalise all responses to the `yield_snapshot` schema
- Handle rate limiting and failures gracefully (one protocol failing must not block others)
- Write to the `yield_snapshots` Supabase table

Supported yield categories:
- **Lending** (e.g., Kamino Finance, MarginFi, Solend)
- **Liquidity Pools** (e.g., Orca Whirlpools, Raydium concentrated)
- **Liquid Staking** (e.g., Jito, Marinade, BlazeStake)
- **Restaking / Yield Vaults** (e.g., Kamino vaults, Drift vaults)

---

## 2.3 API Surface

### Backend REST API (FastAPI — api.yieldsageai.xyz)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/yields/latest` | None | Latest yield snapshots for all active protocols |
| GET | `/api/v1/yields/{protocol_slug}/history` | None | 7-day APY history for a specific protocol |
| GET | `/api/v1/recommendations/latest` | None | Latest top recommendation per risk tier |
| GET | `/api/v1/recommendations/history` | None | Paginated recommendation history with on-chain signatures |
| GET | `/api/v1/protocols` | None | All tracked protocols with metadata |
| GET | `/api/v1/health` | None | Health check — RPC connectivity, DB status |
| POST | `/api/v1/auth/verify` | JWT | Verify Supabase JWT, return user profile |
| PATCH | `/api/v1/users/preferences` | JWT | Update risk preference |
| POST | `/api/v1/telegram/connect` | JWT | Link Telegram chat ID to user account |

### Internal Agent Endpoints (Railway internal — not public)

| Method | Path | Description |
|---|---|---|
| POST | `/internal/trigger/fetch` | Manually trigger a data fetch cycle |
| POST | `/internal/trigger/score` | Manually trigger the AI scoring cycle |
| POST | `/internal/trigger/onchain` | Manually trigger on-chain logging for unlogged recs |
| GET | `/internal/status` | Agent health: last fetch time, last score time, RPC status |

---

## 2.4 Key Technical Constraints

1. **Agent must run continuously** — Railway always-on dyno, not serverless. APScheduler requires a persistent process.
2. **Solana RPC calls must not fail silently** — retry logic required on all `sendTransaction` calls.
3. **On-chain logging is async from scoring** — recommendations are written to DB first, then logged on-chain in a background step. This prevents RPC failures from blocking the AI scoring pipeline.
4. **All LLM calls must have a fallback** — cached last recommendation served if all models are unavailable.
5. **No Dune dependency** — `fetcher.py` must be rewritten from scratch. The `DuneFetcher` class is entirely deprecated.
6. **Mobile-responsive dashboard** — required from day one.
7. **WCAG AA contrast compliance** — all text elements must meet minimum 4.5:1 contrast ratio.
8. **The `ai_model` field is mandatory** — every recommendation must record which LLM model generated it. Required for on-chain auditability.

---

## 2.5 Folder Structure (Target State)

```
yieldsage/
├── agent/                          # Python FastAPI backend
│   ├── main.py                     # FastAPI app entry point
│   ├── scheduler.py                # APScheduler: fetch + score + retry jobs
│   ├── fetcher.py                  # REWRITE: Solana protocol data ingestion
│   ├── scorer.py                   # AI scoring engine (minor updates)
│   ├── logger.py                   # REWRITE: Solana memo logging (replaces Mantle)
│   ├── bot.py                      # Telegram bot (Solscan URL + field name updates)
│   ├── ai_service.py               # Multi-model LLM cascade (prompt updates only)
│   ├── auth.py                     # JWT verification (unchanged)
│   ├── models.py                   # Pydantic models
│   ├── seed.py                     # DB seeding with Solana protocols
│   ├── solana_utils.py             # NEW: Shared Solana helpers
│   ├── quick_solana_check.py       # NEW: Connectivity verification script
│   ├── requirements.txt            # ADD: solders, solana, base58. REMOVE: web3
│   └── routers/
│       ├── yields.py               # /api/v1/yields endpoints
│       ├── recommendations.py      # /api/v1/recommendations endpoints
│       ├── protocols.py            # /api/v1/protocols endpoints
│       └── users.py                # /api/v1/users endpoints
│
├── frontend/                       # Next.js 14 frontend
│   ├── app/
│   │   ├── page.tsx                # Landing page (updated for Solana)
│   │   ├── layout.tsx
│   │   ├── globals.css             # Design system CSS variables
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── signup/page.tsx
│   │   ├── onboarding/page.tsx
│   │   ├── dashboard/page.tsx      # Main leaderboard
│   │   ├── history/page.tsx        # Public recommendation history
│   │   ├── protocol/[slug]/page.tsx
│   │   ├── settings/page.tsx
│   │   └── verify/page.tsx         # NEW: On-chain verification helper
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── leaderboard-table.tsx
│   │   │   ├── recommendation-card.tsx
│   │   │   ├── apy-chart.tsx
│   │   │   └── telegram-connect-banner.tsx
│   │   ├── history/
│   │   │   └── history-table.tsx
│   │   └── layout/
│   │       ├── navbar.tsx
│   │       └── mobile-tab-bar.tsx
│   └── lib/
│       ├── supabase/
│       ├── api.ts
│       ├── solana-explorer.ts      # NEW: Solana Explorer URL builder
│       └── utils.ts
│
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql  # (existing)
│       └── 008_solana_migration.sql  # NEW: chain field updates, column renames
│
├── docs/
│   ├── YIELDSAGE_SOLANA_MIGRATION.md  # This document
│   └── ...
│
├── .env                            # Local env (never commit)
└── .env.example                    # Template (commit this)
```

---

---

# 3. UI/UX Design Specification

## 3.1 Aesthetic Direction

**Dark mode first. Refined, data-dense, trust-building.**

The visual tone sits between Linear (tight, purposeful layout) and a Bloomberg terminal (data credibility) — with a Solana-native flair: the accent shifts from the old sage green to a **violet-to-cyan gradient** echoing Solana's canonical brand colours.

This is a professional-grade financial intelligence tool. The design must feel:
- **Fast** — every state transition under 150ms
- **Trustworthy** — data-dense but never cluttered
- **Solana-native** — subtle nods to the ecosystem without being kitschy
- **Premium** — the kind of UI someone screenshots and shares

Reference apps: Linear, Arkham Intelligence, Zapper.fi, Drift Protocol

---

## 3.2 Color Palette

| Role | Name | Value | Usage |
|---|---|---|---|
| Background primary | Deep void | `#09090B` | Page background |
| Background surface | Card surface | `#111113` | Cards, sidebar |
| Background elevated | Elevated card | `#18181B` | Hover states, dropdowns |
| Background subtle | Hairline tint | `#27272A` | Table rows, dividers |
| Border default | Subtle border | `rgba(255,255,255,0.08)` | All card borders |
| Border focus | Focus ring | `rgba(139,92,246,0.6)` | Keyboard focus |
| Text primary | Snow | `#FAFAFA` | Headings, primary content |
| Text secondary | Zinc 400 | `#A1A1AA` | Subtext, labels |
| Text muted | Zinc 600 | `#52525B` | Tertiary info, placeholders |
| **Accent primary** | **Solana violet** | **`#9945FF`** | **CTAs, active nav, highlights** |
| **Accent secondary** | **Solana cyan** | **`#14F195`** | **Positive APY, success states** |
| Accent gradient | Solana brand | `linear-gradient(135deg, #9945FF 0%, #14F195 100%)` | Hero, top recommendation |
| Stable tag | Calm blue | `#60A5FA` | Low-risk labels |
| Moderate tag | Amber | `#F59E0B` | Mid-risk labels |
| Aggressive tag | Coral | `#F87171` | High-risk labels |
| Success | Mint | `#14F195` | Positive delta, up trend |
| Warning | Amber | `#F59E0B` | Stale data warnings |
| Danger | Red | `#EF4444` | Errors, negative delta |

> **Design Rule:** The Solana gradient is reserved exclusively for the top-pick recommendation card header, the landing page hero, and the primary CTA button. Everywhere else uses flat violet `#9945FF`. Overusing the gradient dilutes its impact.

---

## 3.3 Typography

| Role | Font | Size | Weight | Usage |
|---|---|---|---|---|
| Display hero | Instrument Serif | 56–72px | 400 | Landing page headline only |
| Section heading | DM Sans | 22–28px | 600 | Dashboard section titles |
| UI headings | DM Sans | 16–20px | 500 | Card titles, page headers |
| Body text | DM Sans | 14–16px | 400 | Descriptions, AI reasoning |
| **Data / APY / numbers** | **DM Mono** | **14–22px** | **500** | **All numeric values** |
| Labels / badges | DM Sans | 11px | 600 | Risk tags, column headers |
| Code / addresses | DM Mono | 12px | 400 | Solana addresses, tx signatures |

All fonts self-hosted via `next/font/google` — no layout shift, no external font requests in production.

---

## 3.4 Component Design Spec

### Cards

```css
.card {
  background: #111113;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 24px;
  transition: border-color 150ms ease;
}
.card:hover {
  border-color: rgba(153, 69, 255, 0.3);
}
```

### Top Recommendation Card (Gradient Treatment)

```css
.recommendation-card-top {
  border-left: 3px solid;
  border-image: linear-gradient(180deg, #9945FF 0%, #14F195 100%) 1;
  background: linear-gradient(
    135deg,
    rgba(153, 69, 255, 0.06) 0%,
    rgba(20, 241, 149, 0.04) 100%
  );
}
```

### Buttons — Primary

```css
.btn-primary {
  background: linear-gradient(135deg, #9945FF 0%, #7B2FBE 100%);
  color: #FAFAFA;
  font-family: 'DM Sans', sans-serif;
  font-weight: 500;
  font-size: 14px;
  padding: 10px 20px;
  border-radius: 8px;
  border: none;
  transition: opacity 150ms ease, transform 100ms ease;
}
.btn-primary:hover  { opacity: 0.9; }
.btn-primary:active { transform: scale(0.98); }
```

### Buttons — Secondary

```css
.btn-secondary {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #A1A1AA;
  padding: 10px 20px;
  border-radius: 8px;
}
.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(153, 69, 255, 0.4);
  color: #FAFAFA;
}
```

### Risk Badges

```css
.badge {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  font-family: 'DM Sans', sans-serif;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.badge-stable     { background: rgba(96,165,250,0.15); color: #60A5FA; }
.badge-moderate   { background: rgba(245,158,11,0.15); color: #F59E0B; }
.badge-aggressive { background: rgba(248,113,113,0.15); color: #F87171; }
```

### Tables (Leaderboard)

```css
tr:nth-child(even) { background: rgba(255,255,255,0.02); }
tr:hover           { background: rgba(153,69,255,0.06); }
th {
  font-size: 11px; font-weight: 600;
  color: #52525B; text-transform: uppercase; letter-spacing: 0.08em;
}
td            { font-size: 14px; color: #FAFAFA; }
td.numeric    { font-family: 'DM Mono'; text-align: right; }
```

### Charts (Recharts Configuration)

```
No grid lines (cleaner, more premium).
X-axis: DM Mono, color #52525B.
Line: color #14F195 (Solana cyan), stroke-width 2, no dots.
Area fill: rgba(20, 241, 149, 0.08) below the line.
Tooltip: card-surface background (#111113), 1px border.
```

### Solana Explorer Links (in-app)

```
Format: "chain-icon  <first6>...<last4>"
Font: DM Mono, color: #14F195
On click: opens https://solscan.io/tx/<signature> in new tab
Copy-to-clipboard on click, "Copied!" tooltip for 2s
```

---

## 3.5 Key Screen Layouts

### Dashboard (Desktop 1280px+)

```
┌─────────────────────────────────────────────────────────────┐
│  NAVBAR: [YieldSage]  Dashboard  History  Verify   [Avatar] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  TODAY'S TOP PICK                  [gradient border] │  │
│  │  Kamino USDC Lending                    APY: 8.42%  │  │
│  │  "Low-volatility stablecoin yield backed by $210M   │  │
│  │   TVL. Rate stable for 14 days."   [STABLE]         │  │
│  │  ⛓ Verify: 3xHk7...f9aQ           [View full ->]   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  YIELD LEADERBOARD              [Sort: APY v]  [Risk v]     │
│  ┌────────────────────────────────────────────────────┐    │
│  │ # │ Protocol       │ Pool       │ Risk │  APY   │ 7d │  │
│  │ 1 │ Kamino Finance │ USDC Lend  │  S  │ 8.42% │ up │  │
│  │ 2 │ Jito           │ jitoSOL    │  S  │ 7.18% │ -- │  │
│  │ 3 │ Orca Whirlpool │ SOL/USDC   │  M  │ 24.3% │ up │  │
│  │ 4 │ MarginFi       │ SOL Lend   │  M  │ 19.7% │ dn │  │
│  │ 5 │ Raydium        │ SOL/USDC   │  A  │ 47.2% │ up │  │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  APY HISTORY    [Kamino] [Jito] [Orca] [MarginFi]           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  (line chart — 7 days default, toggle to 30 days)   │  │
│  └──────────────────────────────────────────────────────┘  │
│  [Telegram connect banner — if not connected]               │
└─────────────────────────────────────────────────────────────┘
```

### Mobile Dashboard (375px)

```
┌────────────────────┐
│  YieldSage    [⚙] │
├────────────────────┤
│  TODAY'S TOP PICK  │
│  Kamino USDC       │
│  8.42% [STABLE]    │
│  ⛓ 3xHk7...f9aQ   │
├────────────────────┤
│  LEADERBOARD       │
│  ┌──────────────┐  │
│  │ Kamino USDC  │  │
│  │ 8.42% STABLE │  │
│  └──────────────┘  │
│  ┌──────────────┐  │
│  │ Jito jitoSOL │  │
│  │ 7.18% STABLE │  │
│  └──────────────┘  │
├────────────────────┤
│ [🏠][📋][🔗][⚙]  │
└────────────────────┘
```

---

## 3.6 Micro-Animations

| Element | Animation | Spec |
|---|---|---|
| Card hover | Border glow + lift | `border-color` + `translateY(-2px)` in 150ms ease |
| APY value | Number count-up | 500ms on first load |
| Leaderboard row | Background fade on hover | 100ms ease to `rgba(153,69,255,0.06)` |
| Button active | Micro-press | `scale(0.98)` in 100ms |
| Loading state | Skeleton shimmer | Left-to-right shimmer animation over card shapes |
| Page transition | Fade | 200ms opacity fade between routes |
| On-chain link | Copy feedback | "Copied!" tooltip for 2s on click |

---

## 3.7 Accessibility Requirements

- All body text meets WCAG AA minimum 4.5:1 contrast against `#09090B` background
- Risk badges always include text label — never color alone
- All interactive elements have visible focus states (2px violet outline)
- Charts include accessible data table alternative (toggle below each chart)
- All icon-only buttons have `aria-label`
- Touch targets minimum 44px height on mobile
- All flows functional via keyboard navigation alone

---

---

# 4. App Flow and User Journeys

## 4.1 Page Routes

| Route | Page Name | Auth Required | Description |
|---|---|---|---|
| `/` | Landing | No | Hero, live sample recommendation, how-it-works, CTA |
| `/login` | Login | No | Email + Google OAuth |
| `/signup` | Sign Up | No | Email + Google OAuth |
| `/onboarding` | Onboarding | Yes (new) | Risk preference + Telegram connect |
| `/dashboard` | Dashboard | Yes | Live leaderboard, top pick, APY chart |
| `/history` | History | No | Public recommendation log with on-chain proof |
| `/protocol/[slug]` | Protocol Detail | No | APY trend, AI notes, risk, program address |
| `/settings` | Settings | Yes | Notification prefs, risk update, Telegram |
| `/verify` | Verify | No | On-chain proof verification helper |
| `404` | Not Found | No | Friendly error page |

---

## 4.2 Navigation Structure

**Desktop (top navbar):**
```
[YieldSage logo]    Dashboard | History | Verify    [Settings] [Avatar]
```

**Mobile (bottom tab bar — 4 tabs):**
```
[Home]  [History]  [Verify]  [Settings]
```

---

## 4.3 Landing Page Structure

A new visitor lands on `/`. They see:

1. **Hero section:** Instrument Serif headline — *"Know where your SOL earns best. Today."* — with a one-sentence subline
2. **Live top recommendation** (public, no auth) — today's #1 pick with AI reasoning snippet and Solscan link
3. **How it works** — 3-step explainer: Fetch data -> Score with AI -> Verify on Solana
4. **Leaderboard preview** — read-only table showing top 5 yields, rows 3–5 blurred with "Sign up to see all" prompt
5. **On-chain proof callout** — the trust hook: every recommendation is permanently on Solana
6. **Single CTA:** "Start for free" -> `/signup`

---

## 4.4 Auth Flow

```
/signup
  -> [Enter email + password] OR [Continue with Google]
  -> Email verification sent
  -> User clicks link -> /onboarding
     -> Step 1: Select risk preference (Stable / Moderate / Aggressive / All)
     -> Step 2: Connect Telegram (optional — generates one-time /connect code)
     -> -> /dashboard

Returning user:
/login -> [Credentials / Google] -> /dashboard
```

---

## 4.5 Core User Journey 1 — First Recommendation

1. Visitor lands on `/`, sees today's top pick on Solana with Solscan link
2. Clicks "Verify on Solana" — Solscan opens, shows the memo transaction
3. Impressed by verifiability, clicks "Start for free"
4. Signs up -> onboarding -> selects "Stable" risk, connects Telegram
5. Arrives at `/dashboard`, sees full leaderboard filtered to Stable
6. Clicks the top recommendation — reads 3-sentence AI reasoning
7. Clicks "Verify on Solana" — Solscan shows the on-chain proof
8. Makes their first DeFi deployment on Kamino Finance

---

## 4.6 Core User Journey 2 — Telegram Power User

1. User connected Telegram during onboarding
2. At 8:00 AM UTC receives: "YieldSage Daily | Top Stable: Kamino USDC — 8.42% APY. $210M TVL. solscan.io/tx/3xHk7..."
3. Types `/best aggressive` in the bot
4. Bot replies in < 3 seconds with top aggressive pick + AI reasoning + Solscan link
5. Types `/top5` — bot replies with top 5 across all risk tiers
6. Deploys capital based on recommendation

---

## 4.7 Core User Journey 3 — The Sceptic (Verification Flow)

1. Visitor hears about YieldSage, lands on `/history` (public, no auth)
2. Sees every past recommendation: date, protocol, risk tag, APY, Solana tx signature
3. Clicks "Verify" on a recommendation from 3 weeks ago
4. Solscan shows timestamp and memo: `yieldsage:6e3d8f2a...`
5. Visitor copies the hash, computes it from the displayed JSON, confirms match
6. Trust established. Signs up.

---

## 4.8 Verify Page (/verify)

Dedicated page for on-chain proof verification:
1. User pastes a Solana transaction signature
2. YieldSage fetches the on-chain memo data via Solscan API
3. Displays decoded recommendation hash
4. Fetches matching recommendation from DB
5. Recomputes hash client-side
6. Shows: ✅ Hash verified | ❌ Hash mismatch

---

## 4.9 Empty States

| Context | Message |
|---|---|
| Dashboard — no data yet | "YieldSage is warming up. First recommendations appear within the hour." |
| History — no recs yet | "No recommendations yet. Check back after the first daily run." |
| Protocol detail — new | "Not enough historical data yet. Come back tomorrow." |
| Settings — Telegram not connected | "Connect Telegram for daily AI picks." + Connect button |

---

## 4.10 Error States

| Error | Behaviour |
|---|---|
| LLM API timeout | Show cached last recommendation with "Last updated X hours ago" badge |
| Solana RPC failure | Log silently to `agent_errors`, retry up to 3 times. Never shown to user. |
| Network error on dashboard | "Could not load — retrying..." with spinner. Auto-retry every 30s. |
| Auth session expired | Redirect to `/login` with "Session expired" toast |
| Protocol API down | Skip that protocol for this cycle, log to `agent_errors`, show stale data with timestamp |

---

---

# 5. Backend Architecture Schema

## 5.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   RAILWAY (Python Backend)                  │
│                                                             │
│  FastAPI App     APScheduler         Telegram Bot           │
│  (main.py)       (scheduler.py)      (bot.py)               │
│      |                |                  |                  │
│      |          Scheduled Jobs           |                  │
│      |          fetch_all() [1h]         |                  │
│      |          score_all() [1h]         |                  │
│      |          retry_onchain() [6h]     |                  │
│      |          cleanup_old() [daily]    |                  │
│      |                |                  |                  │
│  ┌───┴────────────────┴──────────────────┴──────────────┐  │
│  │          Core Modules                                 │  │
│  │  fetcher.py   scorer.py   logger.py   ai_service.py  │  │
│  │  (Solana      (LLM        (Solana     (NVIDIA NIM     │  │
│  │   data)        scoring)    Memo)       + Groq +        │  │
│  │                                        Cerebras)      │  │
│  └────────────────────────┬──────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────┘
                            |
           ┌────────────────┼────────────────┐
           |                |                |
  ┌────────┴──────┐  ┌──────┴──────┐  ┌─────┴──────────────┐
  │   Supabase    │  │  Solana     │  │  Solana Protocol   │
  │  PostgreSQL   │  │  Mainnet    │  │  APIs (custom      │
  │               │  │  (Helius    │  │  data pipeline)    │
  │               │  │   RPC)      │  │                    │
  └───────────────┘  └─────────────┘  └────────────────────┘
```

---

## 5.2 Scheduled Jobs

| Job | Function | Schedule | Description |
|---|---|---|---|
| Data Fetch | `fetch_all()` | Every hour | Pulls fresh APY/TVL from all active protocols |
| AI Scoring | `score_and_notify()` | Every hour | Generates recommendations, sends Telegram pushes |
| On-Chain Retry | `retry_failed_onchain_logs()` | Every 6 hours | Retries unlogged recommendations |
| DB Cleanup | `cleanup_old_snapshots()` | Daily 02:00 UTC | Removes snapshots older than 90 days |
| Health Ping | `health_check()` | Every 15 min | Verifies RPC connectivity |

---

## 5.3 Hourly Scoring Pipeline Data Flow

```
scheduler.py
    |
    +-- fetch_all()
    |       |
    |       +-- fetch_protocol_A() -> write to yield_snapshots
    |       +-- fetch_protocol_B() -> write to yield_snapshots
    |       +-- fetch_protocol_N() -> write to yield_snapshots
    |
    +-- score_and_notify()
            |
            +-- get_recent_yields()        <- read yield_snapshots
            |
            +-- AIService.generate_hourly_analysis()   <- NVIDIA NIM
            |       |
            |       +-- for each risk tier:
            |               +-- INSERT into recommendations (no tx_sig yet)
            |               +-- build_payload()
            |               +-- hash_payload()          <- SHA-256
            |               +-- log_recommendation_solana()
            |                       +-- Build Memo instruction
            |                       +-- sendTransaction() via Helius RPC
            |                       +-- UPDATE recommendations.on_chain_tx_signature
            |
            +-- for each user with Telegram:
                    +-- send_daily_push(user, top_picks)
```

---

## 5.4 logger.py Module Interface

Key functions (full implementation in Section 8):

```python
def build_recommendation_payload(
    protocol_name: str, pool_name: str, program_address: str,
    risk_tag: str, rank: int, apy_at_time: float, tvl_usd: float,
    ai_reasoning: str, ai_model: str, scored_at: datetime,
    data_source_id: str = "solana_custom_pipeline",
) -> dict:
    """Builds deterministic canonical payload. scored_at MUST be set before LLM call."""

def hash_payload(payload: dict) -> str:
    """SHA-256 hex digest with sort_keys=True, no extra whitespace."""

def log_recommendation_solana(
    payload: dict, max_retries: int = 3
) -> tuple[str | None, str | None]:
    """
    Sends SPL Memo transaction on Solana Mainnet.
    Returns (tx_signature, rec_hash) on success.
    Returns (None, rec_hash) on failure — hash always returned for DB storage.
    """

def get_solscan_url(tx_signature: str) -> str:
    """Returns https://solscan.io/tx/<signature>"""
```

**Key differences from Mantle logger:**
- Uses `solders` library instead of `web3.py`
- Transaction built as Solana tx with Memo instruction (not EVM tx with `data` field)
- Returns base58 transaction **signature** (~88 chars) not EVM hex hash
- Gas paid in SOL lamports, not MNT
- Explorer URL is Solscan, not Mantlescan

---

## 5.5 fetcher.py Interface Contract

> FULL REWRITE REQUIRED. `DuneFetcher` is entirely deprecated.
> Specific data source TBD — implement against this contract:

```python
class SolanaFetcher:
    async def fetch_all(self) -> list[YieldSnapshot]:
        """Fetches from all active protocols. One failure must not block others."""

    async def fetch_protocol(self, slug: str) -> YieldSnapshot | None:
        """Fetches single protocol. Returns None on failure (not raises)."""

class YieldSnapshot(BaseModel):
    protocol_slug: str
    asset: str                    # e.g., "USDC", "SOL", "jitoSOL"
    apy: Decimal                  # Current APY
    base_apy: Decimal | None      # Base yield without rewards
    reward_apy: Decimal | None    # Reward token yield
    tvl_usd: Decimal | None       # TVL in USD
    reward_tokens: str | None     # e.g., "JTO,SOL"
    apy_1d: Decimal | None
    apy_7d: Decimal | None
    apy_30d: Decimal | None
    fetched_at: datetime
    raw_payload: dict             # Full API response for audit
```

---

---

# 6. Database Schema

## 6.1 Schema Overview

The v2 schema evolves from v1. Structure is preserved; only chain-specific fields are updated.

```
users               <- unchanged
protocols           <- chain field: 'solana'; program_address replaces pool_address; category added
yield_snapshots     <- unchanged structure
recommendations     <- on_chain_tx_hash renamed to on_chain_tx_signature; tvl_usd_at_time added
telegram_messages   <- unchanged
alert_preferences   <- unchanged
agent_errors        <- unchanged
chat_memory         <- unchanged (from migration 004)
paper_trades        <- unchanged (from migration 004)
```

---

## 6.2 Table: users

```sql
CREATE TABLE public.users (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT        NOT NULL UNIQUE,
    full_name           TEXT,
    telegram_chat_id    BIGINT      UNIQUE,
    risk_preference     TEXT        DEFAULT 'stable,moderate,aggressive',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);
```

---

## 6.3 Table: protocols (Updated for Solana)

```sql
CREATE TABLE public.protocols (
    id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT    UNIQUE NOT NULL,    -- e.g. 'kamino-usdc'
    name            TEXT    NOT NULL,            -- e.g. 'Kamino Finance'
    pool_name       TEXT    NOT NULL,            -- e.g. 'USDC Lending'
    program_address TEXT,                        -- Solana base58 program/pool address (NEW)
    risk_tag        TEXT    NOT NULL,            -- 'stable' | 'moderate' | 'aggressive'
    chain           TEXT    DEFAULT 'solana',    -- was 'mantle'
    category        TEXT,                        -- 'lending' | 'liquidity_pool' | 'liquid_staking' | 'vault' (NEW)
    source_url      TEXT,
    explorer_url    TEXT,                        -- Solscan address page (NEW)
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

**New fields vs v1:**
- `program_address` — replaces `pool_address`. Solana uses base58 public keys.
- `category` — new field for protocol classification
- `explorer_url` — pre-computed Solscan link for the program

### Seed Data (8 Initial Protocols)

| slug | name | pool_name | category | risk_tag |
|---|---|---|---|---|
| `kamino-usdc-lending` | Kamino Finance | USDC Lending | lending | stable |
| `kamino-sol-lending` | Kamino Finance | SOL Lending | lending | moderate |
| `jito-sol-staking` | Jito | jitoSOL Staking | liquid_staking | stable |
| `marinade-sol-staking` | Marinade Finance | mSOL Staking | liquid_staking | stable |
| `orca-sol-usdc` | Orca Whirlpools | SOL/USDC Whirlpool | liquidity_pool | moderate |
| `raydium-sol-usdc` | Raydium | SOL/USDC Concentrated | liquidity_pool | aggressive |
| `marginfi-sol` | MarginFi | SOL Lending | lending | moderate |
| `drift-usdc` | Drift Protocol | USDC Vault | vault | moderate |

---

## 6.4 Table: yield_snapshots

```sql
CREATE TABLE public.yield_snapshots (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id     UUID        REFERENCES public.protocols(id) ON DELETE CASCADE,
    asset           TEXT        NOT NULL,           -- e.g., 'USDC', 'SOL', 'jitoSOL'
    apy             NUMERIC(18,8),
    base_apy        NUMERIC(18,8),
    reward_apy      NUMERIC(18,8),
    tvl_usd         NUMERIC(20,2),
    reward_tokens   TEXT,                           -- e.g., 'JTO,SOL'
    apy_1d          NUMERIC(18,8),
    apy_7d          NUMERIC(18,8),
    apy_30d         NUMERIC(18,8),
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload     JSONB
);

CREATE INDEX idx_yield_snapshots_protocol_time
    ON public.yield_snapshots (protocol_id, fetched_at DESC);
CREATE INDEX idx_yield_snapshots_fetched_at
    ON public.yield_snapshots (fetched_at DESC);
```

---

## 6.5 Table: recommendations (Key Changes Highlighted)

```sql
CREATE TABLE public.recommendations (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id             UUID        REFERENCES public.protocols(id) ON DELETE CASCADE,
    risk_tag                TEXT        NOT NULL,
    rank                    INTEGER     NOT NULL,
    apy_at_time             NUMERIC(10,4) NOT NULL,
    tvl_usd_at_time         NUMERIC(20,2),          -- NEW: TVL at time of recommendation
    ai_reasoning            TEXT        NOT NULL,
    ai_model                TEXT        NOT NULL,
    recommendation_hash     TEXT        NOT NULL,
    on_chain_tx_signature   TEXT        UNIQUE,     -- RENAMED from on_chain_tx_hash (Solana base58, ~88 chars)
    on_chain_logged_at      TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_recommendations_risk_time
    ON public.recommendations (risk_tag, created_at DESC);
CREATE INDEX idx_recommendations_hash
    ON public.recommendations (recommendation_hash);
```

**Critical change:** `on_chain_tx_hash` (EVM hex) renamed to `on_chain_tx_signature` (Solana base58, ~88 chars).

Solana signature format example: `3YdxUcPQ8h6JcKvLMnbR...` (87–88 base58 characters)

---

## 6.6 Table: telegram_messages

```sql
CREATE TABLE public.telegram_messages (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        REFERENCES public.users(id) ON DELETE CASCADE,
    chat_id         BIGINT      NOT NULL,
    message_type    TEXT        NOT NULL,   -- 'daily_push' | 'query_response' | 'alert'
    content         TEXT        NOT NULL,
    sent_at         TIMESTAMPTZ DEFAULT now(),
    status          TEXT        DEFAULT 'pending', -- 'pending' | 'sent' | 'failed'
    error_message   TEXT
);
```

---

## 6.7 Table: alert_preferences

```sql
CREATE TABLE public.alert_preferences (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                     UUID        REFERENCES public.users(id) ON DELETE CASCADE UNIQUE,
    stable_apy_threshold        NUMERIC(6,2),
    moderate_apy_threshold      NUMERIC(6,2),
    aggressive_apy_threshold    NUMERIC(6,2),
    is_active                   BOOLEAN     DEFAULT true,
    created_at                  TIMESTAMPTZ DEFAULT now(),
    updated_at                  TIMESTAMPTZ DEFAULT now()
);
```

---

## 6.8 Table: agent_errors

```sql
CREATE TABLE public.agent_errors (
    id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type        TEXT    NOT NULL,
    -- 'fetch' | 'score' | 'onchain_log' | 'telegram_push' | 'health'
    error_message   TEXT    NOT NULL,
    stack_trace     TEXT,
    retry_count     INTEGER DEFAULT 0,
    resolved        BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 6.9 Migration SQL: 008_solana_migration.sql

```sql
-- Migration 008: Mantle to Solana chain migration
-- Run after: 007_add_image_url_and_app_link.sql

-- 1. Update protocols table — new Solana-specific columns
ALTER TABLE public.protocols
    ADD COLUMN IF NOT EXISTS program_address TEXT,
    ADD COLUMN IF NOT EXISTS category TEXT,
    ADD COLUMN IF NOT EXISTS explorer_url TEXT;

-- Rename pool_address to program_address (Solana terminology)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='protocols' AND column_name='pool_address'
    ) THEN
        ALTER TABLE public.protocols RENAME COLUMN pool_address TO program_address;
    END IF;
END $$;

-- Update chain default from 'mantle' to 'solana'
ALTER TABLE public.protocols ALTER COLUMN chain SET DEFAULT 'solana';
UPDATE public.protocols SET chain = 'solana'
WHERE chain = 'mantle' OR chain IS NULL;

-- 2. Update recommendations table
-- Rename on_chain_tx_hash to on_chain_tx_signature
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='recommendations' AND column_name='on_chain_tx_hash'
    ) THEN
        ALTER TABLE public.recommendations
            RENAME COLUMN on_chain_tx_hash TO on_chain_tx_signature;
    END IF;
END $$;

-- Add TVL at time of recommendation
ALTER TABLE public.recommendations
    ADD COLUMN IF NOT EXISTS tvl_usd_at_time NUMERIC(20,2);

-- 3. Add useful indexes
CREATE INDEX IF NOT EXISTS idx_recommendations_hash
    ON public.recommendations (recommendation_hash);

CREATE INDEX IF NOT EXISTS idx_protocols_category
    ON public.protocols (category);

-- 4. Clear old Mantle protocol data (seed.py will insert Solana protocols)
DELETE FROM public.yield_snapshots WHERE protocol_id IN (
    SELECT id FROM public.protocols WHERE chain = 'mantle'
);
DELETE FROM public.recommendations WHERE protocol_id IN (
    SELECT id FROM public.protocols WHERE chain = 'mantle'
);
DELETE FROM public.protocols WHERE chain = 'mantle';

-- 5. Add column comments for clarity
COMMENT ON COLUMN public.recommendations.on_chain_tx_signature IS
    'Solana transaction signature (base58, ~88 chars) of the on-chain SPL Memo log';
COMMENT ON COLUMN public.protocols.program_address IS
    'Solana on-chain program or pool address (base58 public key)';
COMMENT ON COLUMN public.protocols.category IS
    'Protocol category: lending | liquidity_pool | liquid_staking | vault';
```

---

## 6.10 Row Level Security Summary

| Table | anon | authenticated | service_role |
|---|---|---|---|
| `users` | — | Read/update own row | Full access |
| `protocols` | Read all | Read all | Full access |
| `yield_snapshots` | Read all | Read all | Full access |
| `recommendations` | Read all | Read all | Full access |
| `telegram_messages` | — | Read own rows | Full access |
| `alert_preferences` | — | Read/write own row | Full access |
| `agent_errors` | — | — | Full access |
| `chat_memory` | — | Read own rows | Full access |
| `paper_trades` | — | Read/write own rows | Full access |

---

---

# 7. Implementation Plan

## Phase Overview

```
Phase 1: Foundation Setup           Days 1-2
Phase 2: Database Migration         Days 2-3
Phase 3: Solana Logger Rewrite      Days 3-4
Phase 4: Fetcher Rewrite            Days 4-6   (BLOCKED: awaiting data source spec)
Phase 5: AI Scoring Updates         Day 6
Phase 6: Bot and Scheduler Updates  Days 6-7
Phase 7: Frontend Updates           Days 7-9
Phase 8: Integration Testing        Days 9-11
Phase 9: Deployment and Monitoring  Days 11-12
```

---

## Phase 1: Foundation Setup

**Goal:** All dependencies, environment variables, and scaffolding updated for Solana. Zero active Mantle code paths.

### Tasks

- [ ] Update `agent/requirements.txt`:
  ```diff
  - web3>=6.0.0
  + solders>=0.21.0
  + solana>=0.35.0
  + base58>=2.1.0
  ```

- [ ] Create new Solana environment variables (see Section 10)
  - `SOLANA_RPC_URL` (Helius or QuickNode)
  - `SOLANA_RPC_URL_FALLBACK`
  - `YIELDSAGE_SOLANA_WALLET_KEYPAIR`
  - Remove: `MANTLE_RPC_URL`, `YIELDSAGE_WALLET_PRIVATE_KEY`, `DUNE_API_KEYS`

- [ ] Update `.env.example` with all new Solana variables documented

- [ ] Archive deprecated files (rename, do not delete):
  - `agent/logger.py` -> `agent/logger_mantle_deprecated.py`

- [ ] Create empty stubs: `agent/logger.py`, `agent/solana_utils.py`

**Done criteria:** `pip install -r requirements.txt` succeeds. Solana imports work. No active Mantle imports.

---

## Phase 2: Database Migration

**Goal:** Supabase schema updated. All tables reflect v2 schema. Seed data populated with Solana protocols.

### Tasks

- [ ] Write `supabase/migrations/008_solana_migration.sql` (see Section 6.9)
- [ ] Run migration via Supabase dashboard SQL editor or Supabase CLI
- [ ] Update `agent/seed.py` with 8 Solana protocols including `program_address`, `category`, `explorer_url`
- [ ] Run `seed.py` to insert protocols
- [ ] Verify in Supabase table editor:
  - `protocols.chain` = `'solana'` for all rows
  - `recommendations.on_chain_tx_signature` column exists
  - Old Mantle protocol rows deleted

**Done criteria:** All 8 Solana protocols visible in Supabase. Column names match v2 schema. RLS policies pass.

---

## Phase 3: Solana Logger Rewrite

**Goal:** `agent/logger.py` fully implemented for Solana. Test memo transaction lands on Solana Mainnet.

### Tasks

- [ ] Implement `agent/logger.py` (see full spec in Section 8):
  - `build_recommendation_payload()` — updated for Solana fields
  - `hash_payload()` — identical logic, no changes needed
  - `log_recommendation_solana()` — rewritten using `solders` + `solana-py`
  - `get_solscan_url()` — returns `https://solscan.io/tx/<signature>`

- [ ] Create `agent/solana_utils.py`:
  - `get_rpc_client()` — returns Client with Helius primary, public fallback
  - `load_keypair()` — supports base58 string and JSON array formats
  - `get_wallet_balance()` — returns SOL balance

- [ ] Create and fund agent wallet with >= 0.1 SOL:
  - Generate fresh Solana keypair
  - Store as `YIELDSAGE_SOLANA_WALLET_KEYPAIR` in env
  - Fund via Coinbase, Kraken, or Phantom

- [ ] Write and run `agent/quick_solana_check.py`:
  - Verify: keypair loads, RPC connects, balance > 0
  - Send test memo transaction, print signature
  - Verify signature resolves on Solscan

- [ ] Integrate `log_recommendation_solana()` into `scorer.py`:
  - Called immediately after DB insert
  - `on_chain_tx_signature` and `on_chain_logged_at` updated in DB
  - Remove all `mantlescan` references

**Done criteria:** Test memo transaction visible on solscan.io. `quick_solana_check.py` passes all assertions.

---

## Phase 4: Fetcher Rewrite

**Goal:** `agent/fetcher.py` rewritten for new Solana data source. Data flowing into `yield_snapshots` hourly.

> **BLOCKED:** This phase cannot start until the product team confirms the specific data source API.

### Tasks (post-unblock)

- [ ] Receive data source specification from product team
- [ ] Rewrite `agent/fetcher.py` implementing `SolanaFetcher` interface (see Section 5.5)
- [ ] Remove all Dune-specific code: `DuneFetcher`, `DUNE_QUERY_ID`, `DUNE_API_KEYS`, `fetcher_state.json`, `check_key_credits()`, `rotate_key()`
- [ ] Update `agent/scheduler.py`: replace `DuneFetcher` with `SolanaFetcher`
- [ ] Test: run `fetcher.py` manually, confirm `yield_snapshots` populates for all 8 protocols

**Done criteria:** `yield_snapshots` table populated with fresh data. Scheduler runs hourly without errors.

---

## Phase 5: AI Scoring Updates

**Goal:** AI scoring prompts updated for Solana. No Mantle references in any LLM prompt.

### Tasks

- [ ] Update `ai_service.py` system prompts:
  - Replace "Mantle", "MNT", "Mantle Network" with "Solana", "SOL"
  - Update example protocol names (Agni Finance -> Kamino Finance, etc.)
  - Preserve all prompt hardening techniques (LAW framing, examples, self-check)

- [ ] Update `scorer.py`:
  - Import `log_recommendation_solana` from `logger`
  - Store `on_chain_tx_signature` (not `on_chain_tx_hash`)
  - Update yield_context strings for Solana protocol names
  - Confirm `scored_at` set before LLM call (unchanged)
  - Confirm `ai_model` returned from every LLM call (unchanged)

**Done criteria:** `recommendations` table populated with Solana protocol picks. `ai_reasoning` references Solana DeFi. `on_chain_tx_signature` populated.

---

## Phase 6: Bot and Scheduler Updates

**Goal:** Telegram bot updated for Solana. All messages reference Solscan.

### Tasks

- [ ] Update `bot.py`:
  - Replace all `mantlescan.xyz/tx/` -> `solscan.io/tx/`
  - Replace `on_chain_tx_hash` field references -> `on_chain_tx_signature`
  - Update welcome message and help text for Solana context
  - Update all command response formatters

- [ ] Update `scheduler.py`:
  - Register `retry_failed_onchain_logs()` (every 6 hours)
  - Register `cleanup_old_snapshots()` (daily 02:00 UTC)
  - Update `health_check()` to test Solana RPC

- [ ] Test all Telegram commands end-to-end

**Done criteria:** All commands work. All messages include correct Solscan links. Daily push fires at 8:00 AM UTC.

---

## Phase 7: Frontend Updates

**Goal:** Dashboard, history, and all components updated for Solana. No Mantle references visible.

### Tasks

- [ ] Create `frontend/lib/solana-explorer.ts`:
  ```typescript
  export const getSolscanTxUrl = (sig: string) => `https://solscan.io/tx/${sig}`;
  export const getSolscanAddressUrl = (addr: string) => `https://solscan.io/account/${addr}`;
  export const formatSignature = (sig: string) => `${sig.slice(0,6)}...${sig.slice(-4)}`;
  ```

- [ ] Update `recommendation-card.tsx`:
  - `mantlescan.xyz/tx/` -> `solscan.io/tx/`
  - `on_chain_tx_hash` -> `on_chain_tx_signature`
  - "Verify on Mantle" -> "Verify on Solana"
  - Link color: `#4ADE80` -> `#14F195` (Solana cyan)

- [ ] Update `history-table.tsx`:
  - Signature column with shortened display (`3xHk7...f9aQ`)
  - Proof column links to Solscan

- [ ] Build `/app/verify/page.tsx` (on-chain verification page)

- [ ] Update landing page: Solana tagline, Solana protocol examples, Solscan links

- [ ] Update TypeScript interfaces: `on_chain_tx_hash` -> `on_chain_tx_signature`

- [ ] Visual polish: Update accent palette from sage green to Solana violet/cyan

**Done criteria:** No Mantle references visible on any page. All Solscan links resolve. Verify page works.

---

## Phase 8: Integration and End-to-End Testing

**Goal:** Full system test — data flows from source to DB to AI to on-chain to Telegram to Dashboard.

### Test Cases

| # | Test | Expected Result |
|---|---|---|
| T-01 | Run `fetch_all()` manually | All 8 protocols return data. `yield_snapshots` populated. |
| T-02 | Run `score_and_notify()` manually | `recommendations` table has 1 row per risk tier. `ai_reasoning` populated. |
| T-03 | Verify `on_chain_tx_signature` | Each recommendation has non-null signature. Solscan resolves the tx. |
| T-04 | Decode memo on Solscan | Memo field decodes to `yieldsage:<sha256>`. Hash matches DB. |
| T-05 | `/best stable` in Telegram | Returns recommendation with Solscan link. Response < 3s. |
| T-06 | `/top5` in Telegram | Returns 5 recommendations with correct risk tags and Solscan links. |
| T-07 | Dashboard leaderboard | Shows all active protocols, sorted by APY. Updates on refresh. |
| T-08 | History page | Shows all historical recommendations. Solscan links work. |
| T-09 | Verify page | Paste tx signature -> "Hash verified" displayed. |
| T-10 | Retry job | Null a tx_signature in DB -> retry job picks it up and logs it. |
| T-11 | RPC fallback | Disable primary RPC -> system falls back to secondary. No crash. |
| T-12 | LLM fallback | Disable NVIDIA NIM -> Groq responds. Disable both -> cached response served. |
| T-13 | Auth flow | Sign up -> verify -> onboarding -> dashboard. Full round trip. |
| T-14 | Telegram connect | `/connect <code>` links Telegram to Supabase user. `telegram_chat_id` updated. |
| T-15 | Mobile layout | Dashboard at 375px width. No horizontal scroll. Stacked card layout. |

---

## Phase 9: Deployment and Monitoring

**Goal:** Live on Solana Mainnet. Monitoring in place. First 7 days of recommendations logged.

### Tasks

- [ ] Update Railway environment variables (remove Mantle/Dune, add Solana)
- [ ] Update Vercel environment variables
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel
- [ ] Verify first scheduled run in Railway logs
- [ ] Verify first on-chain memo transaction on Solscan
- [ ] Update README: remove Mantle references, add first real Solscan tx link
- [ ] Set up Railway crash alerts
- [ ] Monitor `agent_errors` table daily for first week
- [ ] Confirm 7+ consecutive days of recommendations with `on_chain_tx_signature` before public launch

---

---

# 8. Solana On-Chain Logging Procedure

## 8.1 How It Works — Plain English

Every time `scorer.py` produces a recommendation batch:

1. The recommendation payload is serialised to canonical JSON
2. A SHA-256 hash is computed
3. A Solana transaction is built with a **SPL Memo instruction** containing: `yieldsage:<sha256_hex>`
4. The transaction is signed with the YieldSage Solana keypair and submitted via Helius RPC
5. The returned **transaction signature** (base58, ~88 chars) is stored in `recommendations.on_chain_tx_signature`
6. The frontend renders a clickable `solscan.io/tx/<signature>` link

Anyone can click the link, see the memo on Solscan, and verify the hash matches the database recommendation. Tamper-proof.

---

## 8.2 Payload Schema (Solana v2)

```python
recommendation_payload = {
    "version": "2.0",                               # Schema version — 2.0 for Solana
    "source": "<custom_data_source_id>",            # TBD when data source confirmed
    "scored_at": "2026-07-27T08:00:00Z",            # Set BEFORE calling LLM
    "risk_tag": "stable",                           # "stable" | "moderate" | "aggressive"
    "rank": 1,
    "protocol_name": "Kamino Finance",
    "pool_name": "USDC Lending",
    "program_address": "KLend2g3cP87fffoy8q1mQqGKjrL9jRWKCKEeyEFxBl",  # Solana base58
    "apy_at_time": "8.4200",                        # String, not float (hash determinism)
    "tvl_usd": "210340000.00",                      # String for same reason
    "ai_reasoning": "...",
    "ai_model": "meta/llama-3.3-70b-instruct",
    "chain": "solana",                              # was "mantle"
    "chain_id": 101                                 # Solana mainnet
}
```

---

## 8.3 agent/logger.py — Full Implementation

```python
# agent/logger.py
# On-Chain Verifiability Layer for YieldSage — Solana Mainnet
# Logs SHA-256 recommendation hashes as SPL Memo transactions on Solana
# SPL Memo Program: MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr

import hashlib
import json
import os
import time
import base58
import logging
from datetime import datetime, timezone

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solders.transaction import Transaction
from solders.message import Message
from solana.rpc.api import Client
from solana.rpc.types import TxOpts

logger = logging.getLogger(__name__)

# Configuration
SOLANA_RPC_URL          = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
SOLANA_RPC_URL_FALLBACK = os.environ.get("SOLANA_RPC_URL_FALLBACK", "https://api.mainnet-beta.solana.com")
KEYPAIR_ENV             = os.environ.get("YIELDSAGE_SOLANA_WALLET_KEYPAIR")
MEMO_PROGRAM_ID         = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
SOLSCAN_BASE            = "https://solscan.io/tx/"


def load_keypair() -> Keypair | None:
    """
    Loads agent keypair from YIELDSAGE_SOLANA_WALLET_KEYPAIR env var.
    Supports: base58 string (64-byte) OR JSON array of 64 integers.
    """
    if not KEYPAIR_ENV:
        logger.warning("[logger] YIELDSAGE_SOLANA_WALLET_KEYPAIR not set.")
        return None
    try:
        if KEYPAIR_ENV.strip().startswith("["):
            secret_bytes = bytes(json.loads(KEYPAIR_ENV))
        else:
            secret_bytes = base58.b58decode(KEYPAIR_ENV)
        return Keypair.from_bytes(secret_bytes)
    except Exception as e:
        logger.error(f"[logger] Failed to load keypair: {e}")
        return None


def get_client(use_fallback: bool = False) -> Client:
    url = SOLANA_RPC_URL_FALLBACK if use_fallback else SOLANA_RPC_URL
    return Client(url)


def build_recommendation_payload(
    protocol_name: str,
    pool_name: str,
    program_address: str,
    risk_tag: str,
    rank: int,
    apy_at_time: float,
    tvl_usd: float,
    ai_reasoning: str,
    ai_model: str,
    scored_at: datetime,
    data_source_id: str = "solana_custom_pipeline",
) -> dict:
    """
    Builds the canonical payload dict for Solana recommendations.
    All numeric fields stored as strings for hash determinism.
    scored_at MUST be set before calling the LLM.
    """
    return {
        "version": "2.0",
        "source": data_source_id,
        "scored_at": scored_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "risk_tag": risk_tag,
        "rank": rank,
        "protocol_name": protocol_name,
        "pool_name": pool_name,
        "program_address": program_address,
        "apy_at_time": f"{float(apy_at_time):.4f}",
        "tvl_usd": f"{float(tvl_usd):.2f}",
        "ai_reasoning": ai_reasoning.strip(),
        "ai_model": ai_model,
        "chain": "solana",
        "chain_id": 101,
    }


def hash_payload(payload: dict) -> str:
    """
    Deterministic SHA-256 hex digest.
    sort_keys=True + separators=(',',':') = identical output regardless of dict order.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def log_recommendation_solana(
    payload: dict,
    max_retries: int = 3,
    retry_delay_seconds: float = 5.0,
) -> tuple[str | None, str | None]:
    """
    Sends a Solana transaction with a Memo instruction containing:
      "yieldsage:<sha256_hex>"

    Returns:
        (tx_signature, rec_hash) on success
        (None, rec_hash) on failure -- rec_hash always returned for DB storage
    """
    keypair = load_keypair()
    if not keypair:
        logger.warning("[logger] No keypair loaded. Skipping on-chain log.")
        rec_hash = hash_payload(payload)
        return None, rec_hash

    rec_hash = hash_payload(payload)
    memo_bytes = f"yieldsage:{rec_hash}".encode("utf-8")

    for attempt in range(1, max_retries + 1):
        use_fallback = attempt > 1
        try:
            client = get_client(use_fallback=use_fallback)

            # Get recent blockhash
            blockhash_resp = client.get_latest_blockhash()
            if blockhash_resp.value is None:
                raise RuntimeError("Could not fetch recent blockhash from RPC.")
            recent_blockhash = blockhash_resp.value.blockhash

            # Build SPL Memo instruction
            memo_instruction = Instruction(
                program_id=MEMO_PROGRAM_ID,
                accounts=[AccountMeta(
                    pubkey=keypair.pubkey(),
                    is_signer=True,
                    is_writable=False,
                )],
                data=memo_bytes,
            )

            # Build, sign, and send transaction
            message = Message.new_with_blockhash(
                instructions=[memo_instruction],
                payer=keypair.pubkey(),
                blockhash=recent_blockhash,
            )
            tx = Transaction([keypair], message, recent_blockhash)
            response = client.send_transaction(
                tx,
                opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"),
            )

            if response.value is None:
                raise RuntimeError(f"sendTransaction returned no signature: {response}")

            tx_signature = str(response.value)
            logger.info(f"[logger] On-chain log success (attempt {attempt}): {tx_signature}")
            logger.info(f"[logger]    View: {SOLSCAN_BASE}{tx_signature}")
            return tx_signature, rec_hash

        except Exception as e:
            logger.error(f"[logger] Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay_seconds * attempt)  # Backoff: 5s, 10s
            else:
                logger.critical(
                    f"[logger] All {max_retries} retries exhausted for hash {rec_hash[:12]}. "
                    f"Storing hash without tx_signature."
                )
                return None, rec_hash


def get_solscan_url(tx_signature: str) -> str:
    """Returns the public Solscan URL for a given Solana transaction signature."""
    return f"{SOLSCAN_BASE}{tx_signature}"
```

---

## 8.4 Integration in scorer.py

```python
# 1. Import at top of scorer.py
from logger import (
    build_recommendation_payload,
    log_recommendation_solana,
    get_solscan_url,
)
from datetime import datetime, timezone

# 2. Set scored_at BEFORE calling LLM
scored_at = datetime.now(timezone.utc)   # MUST be before LLM call
picks = await ai_service.generate_hourly_analysis(yields_data)

# 3. For each recommendation:
for pick in picks:
    # Write to DB first (without tx_sig)
    insert_result = supabase.table("recommendations").insert({
        "protocol_id":         pick["protocol_id"],
        "risk_tag":            pick["risk_tag"],
        "rank":                pick["rank"],
        "apy_at_time":         pick["apy"],
        "tvl_usd_at_time":     pick.get("tvl_usd"),
        "ai_reasoning":        pick["reasoning"],
        "ai_model":            pick["model_used"],
        "recommendation_hash": None,
        "on_chain_tx_signature": None,
    }).execute()
    rec_id = insert_result.data[0]["id"]

    # Build canonical payload
    payload = build_recommendation_payload(
        protocol_name  = pick["protocol_name"],
        pool_name      = pick["pool_name"],
        program_address = pick["program_address"],
        risk_tag       = pick["risk_tag"],
        rank           = pick["rank"],
        apy_at_time    = pick["apy"],
        tvl_usd        = pick.get("tvl_usd", 0.0),
        ai_reasoning   = pick["reasoning"],
        ai_model       = pick["model_used"],
        scored_at      = scored_at,
    )

    # Log on-chain
    tx_sig, rec_hash = log_recommendation_solana(payload)

    # Update DB with hash and tx_sig
    update_data = {"recommendation_hash": rec_hash}
    if tx_sig:
        update_data["on_chain_tx_signature"] = tx_sig
        update_data["on_chain_logged_at"] = datetime.now(timezone.utc).isoformat()
    supabase.table("recommendations").update(update_data).eq("id", rec_id).execute()
```

---

## 8.5 Retry Job (scheduler.py)

```python
async def retry_failed_onchain_logs():
    """Retries recommendations hashed but not yet logged on-chain."""
    from logger import log_recommendation_solana, hash_payload, build_recommendation_payload

    result = supabase.table("recommendations") \
        .select("*, protocols(*)") \
        .is_("on_chain_tx_signature", "null") \
        .not_.is_("recommendation_hash", "null") \
        .execute()

    pending = result.data
    if not pending:
        logger.info("[retry_job] No pending on-chain logs.")
        return

    logger.info(f"[retry_job] Found {len(pending)} recommendations missing tx_signature.")

    for rec in pending:
        protocol = rec.get("protocols", {})
        payload = build_recommendation_payload(
            protocol_name   = protocol.get("name", "Unknown"),
            pool_name       = protocol.get("pool_name", "Unknown"),
            program_address = protocol.get("program_address", ""),
            risk_tag        = rec["risk_tag"],
            rank            = rec["rank"],
            apy_at_time     = rec["apy_at_time"],
            tvl_usd         = rec.get("tvl_usd_at_time") or 0.0,
            ai_reasoning    = rec["ai_reasoning"],
            ai_model        = rec["ai_model"],
            scored_at       = datetime.fromisoformat(rec["created_at"]),
        )
        recomputed = hash_payload(payload)
        if recomputed != rec["recommendation_hash"]:
            logger.error(f"[retry_job] Hash mismatch for rec {rec['id']}. Skipping.")
            continue

        tx_sig, _ = log_recommendation_solana(payload, max_retries=2)
        if tx_sig:
            supabase.table("recommendations").update({
                "on_chain_tx_signature": tx_sig,
                "on_chain_logged_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", rec["id"]).execute()
            logger.info(f"[retry_job] Recovered rec {rec['id']}: {tx_sig}")

# Register in scheduler:
scheduler.add_job(retry_failed_onchain_logs, "interval", hours=6, id="retry_onchain")
```

---

## 8.6 Frontend Proof Links

```typescript
// lib/solana-explorer.ts
export const getSolscanTxUrl = (sig: string) => `https://solscan.io/tx/${sig}`;
export const formatSignature = (sig: string) => `${sig.slice(0,6)}...${sig.slice(-4)}`;

// In recommendation-card.tsx:
{rec.on_chain_tx_signature ? (
  <a
    href={getSolscanTxUrl(rec.on_chain_tx_signature)}
    target="_blank"
    rel="noopener noreferrer"
    className="inline-flex items-center gap-1.5 text-xs font-mono
               text-[#14F195] hover:underline underline-offset-2"
    aria-label={`Verify on Solscan (${rec.on_chain_tx_signature})`}
  >
    <span>⛓</span>
    <span>Verify on Solana</span>
    <span className="text-[#52525B]">
      {formatSignature(rec.on_chain_tx_signature)}
    </span>
  </a>
) : (
  <span className="text-xs text-[#52525B] font-mono">Logging pending...</span>
)}
```

---

## 8.7 Verification — How Anyone Confirms the Proof

| Field on Solscan | What It Shows | What It Proves |
|---|---|---|
| Block timestamp | Exact time transaction confirmed | Recommendation existed at this time — cannot be backdated |
| Fee payer | YieldSage agent wallet address | This is the YieldSage agent |
| Fee | ~0.000005 SOL | Not a fund transfer — purely a data anchor |
| Program | SPL Memo (MemoSq4...) | Standard Solana memo program |
| Instruction data | `yieldsage:<sha256_hex>` | Exact recommendation hash committed on-chain |
| Status | Confirmed / Finalized | Transaction is immutable on Solana |

**Manual verification steps:**
1. Find the recommendation in YieldSage history table
2. Note the `recommendation_hash` shown
3. Click "Verify on Solana" -> Solscan opens
4. In instruction data, decode UTF-8: `yieldsage:<hash>`
5. Compare hash in Solscan to hash in YieldSage DB — they must match

---

## 8.8 Agent Wallet Setup (Step by Step)

**Step 1 — Create dedicated agent wallet**
```bash
solana-keygen new --outfile agent-wallet.json
# OR use Phantom: Create new account -> Export Private Key (JSON array)
```

**Step 2 — Fund with SOL for gas**
- Each memo tx costs ~0.000005 SOL
- $5 of SOL covers 10,000+ transactions
- Fund via Coinbase, Kraken, or Phantom transfer

**Step 3 — Set environment variable**
```env
# Use the JSON array from solana-keygen output:
YIELDSAGE_SOLANA_WALLET_KEYPAIR=[174,33,91,...,255]
# OR base58 private key format
YIELDSAGE_SOLANA_WALLET_KEYPAIR=<base58_64byte_key>
```

**Step 4 — Verify connectivity**
```python
# quick_solana_check.py
import os, json
from solana.rpc.api import Client
from solders.keypair import Keypair
import base58

client = Client(os.environ["SOLANA_RPC_URL"])
print("Connected:", client.is_connected())
print("Cluster:", client.get_cluster_nodes())

keypair_env = os.environ["YIELDSAGE_SOLANA_WALLET_KEYPAIR"]
if keypair_env.startswith("["):
    kp = Keypair.from_bytes(bytes(json.loads(keypair_env)))
else:
    kp = Keypair.from_bytes(base58.b58decode(keypair_env))

balance = client.get_balance(kp.pubkey())
print("Wallet:", kp.pubkey())
print("Balance (lamports):", balance.value)
print("Balance (SOL):", balance.value / 1e9)

# Expected output:
# Connected: True
# Wallet: <your_address>
# Balance (SOL): 0.1  (or whatever you funded it with)
```

---

---

# 9. Migration Delta — What Changes vs What Stays

## 9.1 Files That Must Be Fully Rewritten

| File | Reason |
|---|---|
| `agent/logger.py` | `web3.py` -> `solders` + `solana-py`. Entire Mantle code removed. |
| `agent/fetcher.py` | `DuneFetcher` entirely deprecated. New Solana data source. |
| `agent/seed.py` | Solana protocol seed data (new protocols, Solana addresses) |
| `supabase/migrations/008_solana_migration.sql` | New migration file |

## 9.2 Files That Need Targeted Updates

| File | What Changes |
|---|---|
| `agent/scorer.py` | Import `log_recommendation_solana`, field name `on_chain_tx_signature`, prompt context strings |
| `agent/bot.py` | Solscan URLs, field names, Solana context in help text |
| `agent/scheduler.py` | Replace `DuneFetcher` with `SolanaFetcher`, add new jobs |
| `agent/ai_service.py` | System prompts: "Mantle" -> "Solana", update example protocols |
| `agent/requirements.txt` | Remove `web3`, add `solders`, `solana`, `base58` |
| All frontend components with `on_chain_tx_hash` | Rename to `on_chain_tx_signature` |
| All frontend components with `mantlescan.xyz` | Replace with `solscan.io` |

## 9.3 Files That Require No Changes

| File | Reason |
|---|---|
| `agent/ai_service.py` (core LLM logic) | Multi-model cascade unchanged — only prompts updated |
| `agent/auth.py` | JWT verification is chain-agnostic |
| `agent/main.py` | FastAPI app setup unchanged |
| `agent/routers/*.py` | API endpoints unchanged |
| `frontend/app/(auth)/*` | Auth flow unchanged |
| `frontend/contexts/auth-context.tsx` | Supabase auth unchanged |
| `frontend/lib/api.ts` | API client calls unchanged |
| Supabase Auth config | Auth is chain-agnostic |
| `.gitignore`, `railway.toml`, `Procfile` | Deployment config unchanged |

---

---

# 10. Environment Variables Reference

## 10.1 Complete v2 Environment Variables

### Supabase (unchanged)
```env
SUPABASE_URL=https://zegpklbzfmnexdpksuwz.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
NEXT_PUBLIC_SUPABASE_URL=https://zegpklbzfmnexdpksuwz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

### Solana (NEW — replacing Mantle)
```env
# Primary RPC — use Helius or QuickNode (NOT the public endpoint in production)
SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=<YOUR_HELIUS_KEY>

# Fallback RPC — second provider or public endpoint
SOLANA_RPC_URL_FALLBACK=https://api.mainnet-beta.solana.com

# Agent wallet keypair (64-byte, base58 OR JSON array of 64 integers)
# Generate: solana-keygen new --outfile agent-wallet.json
# NEVER commit to git. Railway env vars only.
YIELDSAGE_SOLANA_WALLET_KEYPAIR=<base58_or_json_array>

# Agent wallet public address (for display/funding reference only)
YIELD_SAGE_WALLET_ADDRESS=<base58_public_key>
```

### AI Models (unchanged)
```env
NVIDIA_API_KEY=nvapi-...
GROQ_API_KEY=gsk_...
CEREBRAS_API_KEY=csk-...
OPENROUTER_API_KEY=sk-or-v1-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Telegram (unchanged)
```env
TELEGRAM_BOT_TOKEN=...
```

### App URLs (unchanged)
```env
NEXT_PUBLIC_APP_URL=https://yieldsageai.xyz
NEXT_PUBLIC_FAST_API_BACKEND_URL=https://api.yieldsageai.xyz
FRONTEND_URL=https://yieldsageai.xyz
AGENT_API_SECRET=<random_secret>
```

### Variables to DELETE from Railway and Vercel
```env
# REMOVE THESE:
MANTLE_RPC_URL
YIELDSAGE_WALLET_PRIVATE_KEY
DUNE_API_KEYS
DEFI_JOSH_DUNE_QUERY_API_KEY
CARDANO_DUNE_API_KEY
```

---

---

# 11. Pre-Launch Checklist

## Infrastructure
- [ ] Railway: Solana vars added, Mantle/Dune vars removed
- [ ] Vercel: env vars updated
- [ ] Supabase migration 008 applied successfully
- [ ] Supabase seed: all 8 Solana protocols inserted
- [ ] Agent wallet created and funded with >= 0.1 SOL
- [ ] `SOLANA_RPC_URL` (Helius or QuickNode) configured
- [ ] `SOLANA_RPC_URL_FALLBACK` configured

## Code
- [ ] `agent/logger.py` — Solana Memo implementation complete and tested
- [ ] `agent/fetcher.py` — Solana data pipeline complete (pending data source)
- [ ] `agent/scorer.py` — `log_recommendation_solana()` integrated, field names updated
- [ ] `agent/bot.py` — all Solscan URLs and field names updated
- [ ] `agent/scheduler.py` — all jobs updated, retry job registered
- [ ] `agent/ai_service.py` — prompts updated for Solana context
- [ ] `agent/requirements.txt` — `web3` removed, `solders` + `solana` + `base58` added
- [ ] Frontend — all `mantlescan` references replaced with `solscan.io`
- [ ] Frontend — all `on_chain_tx_hash` renamed to `on_chain_tx_signature`
- [ ] Frontend — `/verify` page implemented and tested

## Verification
- [ ] `quick_solana_check.py` passes: connected, wallet loads, balance > 0
- [ ] First memo transaction confirmed on Solscan
- [ ] Memo data decodes to `yieldsage:<sha256_hex>`
- [ ] SHA-256 hash recomputed from DB matches on-chain memo
- [ ] All T-01 through T-15 test cases pass
- [ ] Daily push fires at 8:00 AM UTC
- [ ] 7+ consecutive days of recommendations logged before public announcement
- [ ] README updated with first real Solscan tx link

## Quality
- [ ] Mobile layout verified at 375px (no horizontal scroll)
- [ ] WCAG AA contrast ratios pass for all text
- [ ] Dashboard loads under 2 seconds
- [ ] All Telegram bot commands respond under 3 seconds
- [ ] `agent_errors` table empty (or all errors resolved) before launch

---

*YieldSage Solana Migration Master Document — v2.0*
*Date: 2026-07-27*
*Data source for Solana yield ingestion: TBD — to be confirmed and integrated in Phase 4*
