-- Run this in Supabase SQL Editor to update the existing yield_snapshots table

-- Drop existing table (no data in it yet, safe to drop)
DROP TABLE IF EXISTS public.yield_snapshots CASCADE;

-- Recreate with all yield snapshot columns
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

-- Re-enable RLS
ALTER TABLE public.yield_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read snapshots" ON public.yield_snapshots FOR SELECT USING (true);

-- Also remove the UNIQUE constraint on pool_address since multiple protocols share pool addresses
-- (e.g. minterest and ondo-yield-assets both use 0x5be26527...)
ALTER TABLE public.protocols DROP CONSTRAINT IF EXISTS protocols_pool_address_key;
