# Database Layer — compliance-agent-v2

**Version:** 2.0 | **Updated:** 2026-03-10

---

## Overview

PostgreSQL 14+ with pgvector extension. SQLAlchemy ORM with a typed `BaseRepository[T]` pattern.

- **17 tables** total (9 core + 8 added via migrations)
- **14 repositories**, all extending `BaseRepository[T]`
- **Bulk operations** via `bulk_insert_mappings` (single commit per batch)
- **4 performance indexes** added in migration 011

---

## Tables

### Core Tables (schema.sql)

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `users` | NetSuite users (1,932 active) | `netsuite_id`, `email`, `department`, `status` |
| `roles` | NetSuite roles (35 tracked) | `netsuite_role_id`, `role_name`, `permissions` (JSONB) |
| `user_roles` | User-role assignments | `user_id` FK, `role_id` FK, `assigned_at` |
| `sod_rules` | 18 SOD rule definitions | `rule_code`, `severity`, `conflicting_permissions` |
| `violations` | Detected SOD violations | `user_id`, `rule_id`, `scan_id`, `severity`, `status` |
| `compliance_scans` | Scan execution history | `scan_type`, `status`, `started_at`, `completed_at` |
| `agent_logs` | Agent execution logs | `agent_name`, `action`, `result` |
| `notifications` | Notification delivery log | `recipient`, `channel`, `status` |
| `audit_trail` | Compliance audit trail | `actor`, `action`, `target_id`, `timestamp` |
| `user_reconciliations` | NetSuite ↔ Okta reconciliation | `netsuite_user_id` *(indexed v2)*, `okta_user_id` *(indexed v2)* |

### Migration Tables

| Table | Migration | Description |
|-------|-----------|-------------|
| `exceptions` | 005 | Approved SOD exceptions with expiry |
| `conversation_summaries` | 006 | Haiku summaries, 90-day TTL, per-user context |
| `answer_feedback` | 007 | Slack 👍/👎/🔧 feedback, LangSmith run_id |
| `sod_permission_map` | 008 | Permission → SOD category mapping |
| `role_pair_conflicts` | 009 | Precomputed conflict matrix (443 rows, all 35 roles) |
| `correction_embeddings` | 010 | pgvector 384-dim MiniLM few-shot corrections |
| `job_role_mappings` | unnumbered | Job title → canonical NetSuite roles (JSONB) |

---

## v2 Performance Indexes (migration 011)

Four indexes that were missing from the original schema — applied with `CONCURRENTLY` to avoid table locks:

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_violation_rule_id ON violations (rule_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_violation_scan_id ON violations (scan_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recon_netsuite_user_id ON user_reconciliations (netsuite_user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recon_okta_user_id ON user_reconciliations (okta_user_id);
```

Apply:
```bash
psql $DATABASE_URL -f database/migrations/011_add_performance_indexes.sql
```

---

## Repository Pattern

### BaseRepository[T]

All 14 repositories extend `BaseRepository[T]` in `repositories/base_repository.py`:

```python
from repositories.base_repository import BaseRepository
from models.database import Violation

class ViolationRepository(BaseRepository[Violation]):
    model = Violation
    # Inherits: get_by_id, get_all, add, update, delete, bulk_create, bulk_update
```

### Bulk Operations (v2)

**Critical:** Use bulk operations for batch writes — not individual commits.

```python
# ✅ GOOD — single DB round-trip (v2 pattern)
session.bulk_insert_mappings(Violation, list_of_dicts)
session.commit()

# ❌ BAD — N commits (pre-v2 pattern, now fixed)
for v in violations:
    session.add(Violation(**v))
    session.commit()
```

`ViolationRepository.bulk_create_violations()` and `RoleRepository.bulk_upsert_roles()` use `bulk_insert_mappings`.

---

## Repository Reference

| Repository | Key Methods |
|-----------|-------------|
| `UserRepository` | `upsert_user`, `get_by_email`, `get_users_with_roles`, `find_high_risk_users` |
| `RoleRepository` | `bulk_upsert_roles` (single commit), `get_by_netsuite_id`, `get_finance_roles` |
| `ViolationRepository` | `bulk_create_violations` (single commit), `get_open_violations`, `get_by_scan_id` |
| `SODRuleRepository` | `get_by_rule_code`, `get_active_rules`, `get_by_severity` |
| `ExceptionRepository` | `find_similar_exceptions` (bounded to 500 rows), `get_active_exceptions` |
| `JobRoleMappingRepository` | `get_by_job_title`, `get_canonical_roles` |
| `SyncMetadataRepository` | `get_latest_sync`, `create_sync_record`, `mark_complete` |
| `UserReconciliationRepository` | `get_unreconciled`, `mark_reconciled` |
| `AuditTrailRepository` | `log_action`, `get_recent_actions` |

---

## Cache Invalidation (v2)

`CacheService` in `services/cache_service.py` has invalidation hooks for write paths:

```python
cache.invalidate_user(user_id)        # clears all mcp:*:user_id keys
cache.invalidate_role(role_id)        # clears all mcp:*:role_id keys  (v2)
cache.invalidate_violations(scan_id)  # clears violation query cache   (v2)
cache.invalidate_rules()              # clears all SOD rule cache       (v2)
```

Call these from repository write methods to keep Redis consistent with DB.

---

## Session Management

```python
from models.database_config import DatabaseConfig

# Context manager (recommended)
with DatabaseConfig().get_session() as session:
    repo = UserRepository(session)
    user = repo.get_by_email("john@example.com")
# Session auto-closed, rollback on exception
```

---

## Common DB Checks

```bash
# User counts
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users WHERE status='ACTIVE';"

# Violation summary
psql $DATABASE_URL -c "SELECT severity, COUNT(*) FROM violations WHERE status='OPEN' GROUP BY severity;"

# Recent syncs
psql $DATABASE_URL -c "SELECT sync_type, status, started_at, users_synced FROM sync_metadata ORDER BY started_at DESC LIMIT 5;"

# Role-pair conflicts
psql $DATABASE_URL -c "SELECT COUNT(*) FROM role_pair_conflicts;"  -- 443

# Job role mappings
psql $DATABASE_URL -c "SELECT job_title, department FROM job_role_mappings ORDER BY department, job_title;"

# Check indexes are applied
psql $DATABASE_URL -c "\d violations"  -- look for idx_violation_rule_id, idx_violation_scan_id
```

---

## Known Pitfalls

| Pitfall | Issue | Fix |
|---------|-------|-----|
| `metadata` as column name | SQLAlchemy reserves this name | Use `sync_metadata`, `user_metadata` etc. |
| Enum values lowercase | DB CHECK constraints expect UPPERCASE | Always use `SyncStatus.PENDING` (value = "PENDING") |
| Insert violation before scan | FK violation: `violations.scan_id` references `compliance_scans` | Create `ComplianceScan` first, then violations |
| page_size=1000 | NetSuite caps at 200, silently truncates | `page_size=200` in `netsuite_client.py` |

See `docs/LESSONS_LEARNED.md` Issues #1, #13, #14, #15 for full context.

---

**Last Updated:** 2026-03-10
