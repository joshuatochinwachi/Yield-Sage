-- Enable pgcrypto for UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Users Table
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Maps to auth.uid() in Supabase
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    telegram_chat_id BIGINT UNIQUE,
    risk_preference TEXT DEFAULT 'stable,moderate,aggressive',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Protocols Table
CREATE TABLE public.protocols (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    pool_name TEXT NOT NULL,
    pool_address TEXT,
    risk_tag TEXT NOT NULL CHECK (risk_tag IN ('stable', 'moderate', 'aggressive')),
    chain TEXT DEFAULT 'solana',
    source_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(name, pool_address)
);

-- 3. Yield Snapshots Table
CREATE TABLE public.yield_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id UUID REFERENCES public.protocols(id) ON DELETE CASCADE,
    asset TEXT NOT NULL,
    apy NUMERIC(18,8),
    base_apy NUMERIC(18,8),
    reward_apy NUMERIC(18,8),
    tvl_usd NUMERIC(20,2),
    reward_tokens TEXT,
    apy_1d NUMERIC(18,8),
    apy_7d NUMERIC(18,8),
    apy_30d NUMERIC(18,8),
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB
);
CREATE INDEX idx_yield_snapshots_protocol_time ON public.yield_snapshots (protocol_id, fetched_at DESC);

-- 4. Recommendations Table
CREATE TABLE public.recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id UUID REFERENCES public.protocols(id) ON DELETE CASCADE,
    risk_tag TEXT NOT NULL CHECK (risk_tag IN ('stable', 'moderate', 'aggressive')),
    rank INTEGER NOT NULL,
    apy_at_time NUMERIC(10,4) NOT NULL,
    ai_reasoning TEXT NOT NULL,
    ai_model TEXT NOT NULL,
    on_chain_tx_hash TEXT UNIQUE,
    on_chain_logged_at TIMESTAMPTZ,
    recommendation_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_recommendations_risk_time ON public.recommendations (risk_tag, created_at DESC);

-- 5. Telegram Messages Table
CREATE TABLE public.telegram_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    chat_id BIGINT NOT NULL,
    message_type TEXT NOT NULL CHECK (message_type IN ('daily_push', 'query_response', 'alert')),
    content TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'failed')),
    error_message TEXT
);

-- 6. Alert Preferences Table
CREATE TABLE public.alert_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE UNIQUE,
    stable_apy_threshold NUMERIC(6,2),
    moderate_apy_threshold NUMERIC(6,2),
    aggressive_apy_threshold NUMERIC(6,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 7. Agent Errors Table
CREATE TABLE public.agent_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL CHECK (job_type IN ('fetch', 'score', 'onchain_log', 'telegram_push')),
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    retry_count INTEGER DEFAULT 0,
    resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ==========================================
-- ROW LEVEL SECURITY (RLS)
-- ==========================================

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.protocols ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yield_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_errors ENABLE ROW LEVEL SECURITY;

-- Users: read/update own row
CREATE POLICY "Users can read own row" ON public.users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own row" ON public.users FOR UPDATE USING (auth.uid() = id);

-- Protocols: public read
CREATE POLICY "Public read protocols" ON public.protocols FOR SELECT USING (true);

-- Snapshots: public read
CREATE POLICY "Public read snapshots" ON public.yield_snapshots FOR SELECT USING (true);

-- Recommendations: public read
CREATE POLICY "Public read recommendations" ON public.recommendations FOR SELECT USING (true);

-- Telegram Messages: user read own
CREATE POLICY "Users read own telegram messages" ON public.telegram_messages FOR SELECT USING (auth.uid() = user_id);

-- Alert Preferences: user read/write own
CREATE POLICY "Users read own alerts" ON public.alert_preferences FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own alerts" ON public.alert_preferences FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update own alerts" ON public.alert_preferences FOR UPDATE USING (auth.uid() = user_id);

-- Note: The service_role key bypasses RLS, so the Python agent has full read/write access.
