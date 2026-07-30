-- ============================================================================
-- Migration 008: PERMANENTLY DELETE all Mantle chain data
-- ============================================================================
-- The Yield-Sage project has fully migrated to Solana.
-- All 175 Mantle protocol rows and their associated yield snapshots are legacy
-- data that should not exist in production. This migration hard-deletes them.
--
-- Run in this exact order to respect foreign key constraints:
-- 1. Delete yield_snapshots that belong to Mantle protocols
-- 2. Delete paper_trades that reference Mantle protocols (if any)
-- 3. Delete the Mantle protocol rows themselves
-- ============================================================================

-- Step 1: Delete all yield snapshots for Mantle protocols
DELETE FROM yield_snapshots
WHERE protocol_id IN (
  SELECT id FROM protocols WHERE chain = 'mantle'
);

-- Step 2: Delete any paper trades referencing Mantle protocols
DELETE FROM paper_trades
WHERE protocol_id IN (
  SELECT id FROM protocols WHERE chain = 'mantle'
);

-- Step 3: Delete any recommendations referencing Mantle protocols
-- (recommendations table stores protocol info in JSONB, so we match by name)
-- Uncomment if your recommendations table has a protocol_id FK:
-- DELETE FROM recommendations
-- WHERE protocol_id IN (
--   SELECT id FROM protocols WHERE chain = 'mantle'
-- );

-- Step 4: Delete all Mantle protocols
DELETE FROM protocols
WHERE chain = 'mantle';

-- ============================================================================
-- Verification — run this after the migration to confirm 0 Mantle rows remain:
-- SELECT chain, COUNT(*) FROM protocols GROUP BY chain ORDER BY COUNT(*) DESC;
-- Expected result: only 'solana' row with ~4808 entries.
-- ============================================================================
