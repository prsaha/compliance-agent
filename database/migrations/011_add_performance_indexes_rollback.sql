-- Rollback 011: Remove performance indexes added in v2
DROP INDEX CONCURRENTLY IF EXISTS idx_violation_rule_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_violation_scan_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_recon_netsuite_user_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_recon_okta_user_id;
