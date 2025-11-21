-- Migration: 002_add_create_at
-- Description: Add create_at column to candidates table
-- Created: 2025-11-21

-- ============================================
-- UP MIGRATION
-- ============================================

-- up
ALTER TABLE candidates ADD COLUMN create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- ============================================
-- DOWN MIGRATION
-- ============================================

-- down
ALTER TABLE candidates DROP COLUMN create_at;