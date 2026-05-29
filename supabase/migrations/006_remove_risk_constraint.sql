-- Migration: Remove risk preference check constraint and set new default to all 3 selected
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_risk_preference_check;
ALTER TABLE public.users ALTER COLUMN risk_preference SET DEFAULT 'stable,moderate,aggressive';
