-- Fix numeric overflow: some Dune APYs are astronomically large (e.g. 3.9e+93)
-- Switch from NUMERIC(18,8) to DOUBLE PRECISION

DROP TABLE IF EXISTS public.yield_snapshots CASCADE;

CREATE TABLE public.yield_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    protocol_id UUID REFERENCES public.protocols(id) ON DELETE CASCADE,
    asset TEXT NOT NULL,
    apy DOUBLE PRECISION,
    base_apy DOUBLE PRECISION,
    reward_apy DOUBLE PRECISION,
    tvl_usd DOUBLE PRECISION,
    reward_tokens TEXT,
    apy_1d DOUBLE PRECISION,
    apy_7d DOUBLE PRECISION,
    apy_30d DOUBLE PRECISION,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB
);

CREATE INDEX idx_yield_snapshots_protocol_time ON public.yield_snapshots (protocol_id, fetched_at DESC);

ALTER TABLE public.yield_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read snapshots" ON public.yield_snapshots FOR SELECT USING (true);
