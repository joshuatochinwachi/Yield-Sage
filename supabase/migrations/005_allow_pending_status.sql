-- Migration 005: Allow 'pending' status for telegram messages queue
ALTER TABLE public.telegram_messages DROP CONSTRAINT IF EXISTS telegram_messages_status_check;
ALTER TABLE public.telegram_messages ADD CONSTRAINT telegram_messages_status_check CHECK (status IN ('pending', 'sent', 'failed'));
ALTER TABLE public.telegram_messages ALTER COLUMN status SET DEFAULT 'pending';
