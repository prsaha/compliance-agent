# compliance-agent-v2 — Project Structure

**Version:** 2.0 | **Updated:** 2026-03-10 | **Status:** Production

---

## Top-Level Layout

```
compliance-agent-v2/
│
├── slack_bot_local.py          # Slack bot (Socket Mode) — main entry point
├── smoke_test_mcp_live.py      # Live smoke test suite (6/12 pass expected)
├── requirements.txt            # Python dependencies (incl. tenacity, pybreaker, structlog)
├── CLAUDE.md                   # Claude Code project guide
├── .env                        # Secrets + feature flags (gitignored)
│
├── mcp/                        # MCP server + 44 tool handlers
├── agents/                     # Autonomous AI agents
├── services/                   # Business logic + external clients
├── repositories/               # Data access layer (BaseRepository[T] pattern)
├── models/                     # SQLAlchemy ORM models
├── connectors/                 # External system connectors
├── utils/                      # Tool router (intent → tool mapping)
├── config/                     # YAML config (role keywords, LLM settings)
├── database/                   # SQL migrations (001-011) + seed data
├── scripts/                    # Management scripts
├── angular-portal/             # Angular 17 admin UI
├── api/                        # FastAPI REST API
├── data/                       # JSON reference data
├── demos/                      # Demo scripts
├── tests/                      # Test suites
├── docs/                       # Documentation (this directory)
└── archive/                    # Archived old docs/scripts
```

---

## Core Directories

### `mcp/` — MCP Server

```
mcp/
├── mcp_server.py               # FastAPI server, JSON-RPC 2.0 endpoint (:8080)
├── mcp_tools.py                # All 44 tool handlers (~5,000 lines)
├── admin_api.py                # 16 JWT-protected admin endpoints
└── tools/                      # Phase-split re-exports (backwards compat)
    ├── collection_tools.py
    ├── analysis_tools.py
    ├── violation_tools.py
    ├── exception_tools.py
    └── admin_tools.py
```

- All tool calls: `POST /mcp` with `X-API-Key: dev-key-12345`
- Admin endpoints: `Authorization: Bearer <JWT>`
- Health: `GET /health` (no auth required)

### `agents/` — Autonomous Agents

```
agents/
├── data_collector.py           # Scheduled NetSuite sync (full daily @ 2 AM, incremental hourly)
├── analyzer.py                 # SOD rule engine + Claude Opus 4.6 analysis
├── orchestrator.py             # Multi-agent coordinator
├── notifier.py                 # Slack/Email/Jira notifications
├── risk_assessor.py            # Risk scoring engine
├── report_generator.py         # Compliance report generation
└── knowledge_base_pgvector.py  # pgvector semantic search (active)
```

### `services/` — Business Logic

```
services/
├── netsuite_client.py          # NetSuite RESTlet API — page_size=200 (v2 fix)
├── cache_service.py            # Redis TTL cache + invalidate_role/violations/rules
├── approval_service.py         # Exception approval routing
├── jira_client.py              # Jira HTTP client (extracted from ApprovalService in v2)
├── correction_service.py       # Correction embeddings + few-shot injection
├── embedding_service.py        # OpenAI / pgvector embedding service
├── role_recommendation_service.py
├── violation_report_service.py
├── okta_client.py              # Okta API client
├── answer_feedback.py          # Slack feedback button handler
├── conversation_summary.py     # Haiku conversation summarizer
└── llm/                        # Multi-provider LLM abstraction (Anthropic/OpenAI/Gemini)
```

### `repositories/` — Data Access Layer

All repositories extend `BaseRepository[T]` which provides: `get_by_id`, `get_all`, `add`, `update`, `delete`, `bulk_create`, `bulk_update`.

```
repositories/
├── base_repository.py              # NEW in v2 — Generic BaseRepository[T]
├── user_repository.py
├── role_repository.py              # bulk_upsert_roles via bulk_insert_mappings (v2)
├── violation_repository.py         # bulk_create_violations via bulk_insert_mappings (v2)
├── sod_rule_repository.py
├── exception_repository.py         # find_similar_exceptions bounded to 500 rows (v2)
├── exemption_repository.py
├── job_role_mapping_repository.py
├── audit_trail_repository.py
├── user_reconciliation_repository.py
├── okta_user_repository.py
├── sync_metadata_repository.py
├── deactivation_approval_repository.py
└── deactivation_log_repository.py
```

### `models/` — ORM Models

```
models/
├── database.py                 # All SQLAlchemy models + 4 new indexes (v2)
├── database_config.py          # Connection pool, session factory
├── answer_feedback.py          # AnswerFeedback model
├── conversation_summary.py     # ConversationSummary model
└── approved_exception.py       # ApprovedException model
```

### `config/` — Configuration Files

```
config/
├── role_keywords.yaml          # SOD role keyword lists — edit without code changes (v2)
├── llm_config.yaml             # LLM provider + model settings
├── llm_config.example.yaml     # Template
└── model_config.py             # Python model constants
```

### `utils/` — Helpers

```
utils/
└── tool_router.py              # Intent→tool mapping (10 groups, 44 tools)
                                # EVERY new tool must be registered here
```

**Tool intent groups:** `access_review`, `violation_query`, `exception_mgmt`, `sod_rules`, `knowledge`, `role_analysis`, `role_risk`, `reporting`, `system`, `remediation`

### `database/` — Migrations & Schema

```
database/
├── schema.sql                  # Full schema DDL
├── schema_extensions.sql       # pgvector + extensions
├── seed_data/
│   └── sod_rules.json          # 18 active SOD rules
└── migrations/
    ├── 005_add_exception_tables.sql
    ├── 006_add_conversation_summaries.sql
    ├── 007_add_answer_feedback.sql
    ├── 008_add_sod_permission_map.sql
    ├── 009_add_role_pair_conflicts.sql
    ├── 010_add_correction_embeddings.sql
    ├── 011_add_performance_indexes.sql       ← v2: 4 missing indexes
    ├── add_job_role_mappings_table.sql
    └── *_rollback.sql                        ← rollback for each numbered migration
```

### `angular-portal/` — Admin UI

Angular 17 standalone components, JWT-in-memory auth, lazy-loaded routes.

```
angular-portal/
├── src/app/
│   ├── auth/                   # JWT login + level guards (L3/L4/L5)
│   ├── dashboard/              # System health, key metrics
│   ├── violations/             # Violation browser + status updates
│   ├── exceptions/             # Exception management
│   ├── sod-rules/              # SOD rule viewer/editor (L4+)
│   └── config/                 # Thresholds, feature flags (L5)
├── proxy.conf.json             # Dev proxy → localhost:8080
└── package.json
```

Dev server: `cd angular-portal && ng serve` → http://localhost:4200

---

## Database Tables (17 total)

| Table | Description | Added |
|-------|-------------|-------|
| `users` | NetSuite users (1,932 active) | schema |
| `roles` | NetSuite roles (35 tracked) | schema |
| `user_roles` | User-role assignments | schema |
| `sod_rules` | 18 SOD rule definitions | schema |
| `violations` | Detected SOD violations | schema |
| `compliance_scans` | Scan execution history | schema |
| `agent_logs` | Agent execution logs | schema |
| `notifications` | Notification delivery log | schema |
| `audit_trail` | Compliance audit trail | schema |
| `user_reconciliations` | NetSuite ↔ Okta reconciliation | schema |
| `exceptions` | Approved SOD exceptions | migration 005 |
| `conversation_summaries` | Haiku conversation context (90d TTL) | migration 006 |
| `answer_feedback` | User feedback (👍/👎/🔧) | migration 007 |
| `sod_permission_map` | Permission → SOD category mapping | migration 008 |
| `role_pair_conflicts` | Precomputed 443-row conflict matrix | migration 009 |
| `correction_embeddings` | pgvector few-shot correction store | migration 010 |
| `job_role_mappings` | Job title → canonical NetSuite roles | unnumbered |

---

## v2 Changes Summary

| File | Change |
|------|--------|
| `services/netsuite_client.py` | `page_size` 1000 → **200** (eliminated 79.2% data loss) |
| `agents/analyzer.py` | Silent exception → `None`; role keywords loaded from YAML |
| `utils/tool_router.py` | +13 previously unreachable tools registered |
| `requirements.txt` | +tenacity, pybreaker, structlog, python-json-logger, PyYAML |
| `slack_bot_local.py` | structlog JSON logging, retry+circuit breaker, ThreadPoolExecutor |
| `repositories/violation_repository.py` | bulk_insert_mappings (N commits → 1) |
| `repositories/role_repository.py` | bulk_insert_mappings (N commits → 1) |
| `repositories/base_repository.py` | NEW: Generic `BaseRepository[T]` |
| `models/database.py` | +4 missing performance indexes |
| `services/cache_service.py` | +`invalidate_role()`, `invalidate_violations()`, `invalidate_rules()` |
| `services/jira_client.py` | NEW: extracted from `ApprovalService` |
| `mcp/admin_api.py` | JWT role check: substring match → exact token match |
| `config/role_keywords.yaml` | NEW: externalised role keyword lists |
| `database/migrations/011_*` | NEW: 4 performance indexes applied |

---

**Last Updated:** 2026-03-10
