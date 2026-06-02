-- Migration: Add image_url and app_link columns to protocols table
ALTER TABLE public.protocols ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE public.protocols ADD COLUMN IF NOT EXISTS app_link TEXT;
