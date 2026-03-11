-- Migration 011: Add missing performance indexes (v2 production fix)
-- Purpose: Four indexes that were missing from the original schema, causing full-table
--          scans on high-frequency query paths.
--
-- Affected tables:
--   violations          — filtered by rule_id and scan_id on every SOD report query
--   user_reconciliations — filtered by netsuite_user_id / okta_user_id on every sync reconciliation
--
-- Safe to run on a live database: CREATE INDEX IF NOT EXISTS is non-destructive.
-- Each index is created CONCURRENTLY to avoid locking the table during backfill.
-- NOTE: CONCURRENTLY cannot run inside a transaction block — run this file with psql
--       using the --single-transaction=off flag (default), or via: psql -f 011_add_performance_indexes.sql

-- 1. violations.rule_id  (used by: get_violation_stats, list_violations, generate_violation_report)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_violation_rule_id
    ON violations (rule_id);

-- 2. violations.scan_id  (used by: every query that joins compliance_scans → violations)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_violation_scan_id
    ON violations (scan_id);

-- 3. user_reconciliations.netsuite_user_id  (used by: sync reconciliation lookup)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recon_netsuite_user_id
    ON user_reconciliations (netsuite_user_id);

-- 4. user_reconciliations.okta_user_id  (used by: Okta ↔ NetSuite reconciliation join)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recon_okta_user_id
    ON user_reconciliations (okta_user_id);
