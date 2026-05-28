-- Phase 5 & 6 Migrations: Advanced AI Memory and Paper Trading

-- 1. Chat Memory Table
-- Stores conversation history for the AI to retain context
CREATE TABLE public.chat_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    telegram_chat_id BIGINT, -- Can be used if user isn't fully signed up yet but is chatting
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index to quickly fetch recent messages for a user/chat
CREATE INDEX idx_chat_memory_user ON public.chat_memory (user_id, created_at DESC);
CREATE INDEX idx_chat_memory_chat_id ON public.chat_memory (telegram_chat_id, created_at DESC);

-- Enable RLS
ALTER TABLE public.chat_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own chat memory" ON public.chat_memory 
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own chat memory" ON public.chat_memory 
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access chat memory" ON public.chat_memory 
    USING (true);


-- 2. Paper Trades Table
-- Allows users to simulate investments and have the AI track performance
CREATE TABLE public.paper_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    protocol_id UUID REFERENCES public.protocols(id) ON DELETE CASCADE NOT NULL,
    simulated_investment_usd DOUBLE PRECISION NOT NULL,
    entry_apy DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ
);

-- Index for fetching active paper trades per user
CREATE INDEX idx_paper_trades_user_active ON public.paper_trades (user_id) WHERE status = 'active';
CREATE INDEX idx_paper_trades_protocol ON public.paper_trades (protocol_id);

-- Enable RLS
ALTER TABLE public.paper_trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own paper trades" ON public.paper_trades 
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own paper trades" ON public.paper_trades 
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own paper trades" ON public.paper_trades 
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Service role full access paper trades" ON public.paper_trades 
    USING (true);
