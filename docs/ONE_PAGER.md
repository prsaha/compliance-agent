# AI-Powered SOD Compliance System
**Fivetran Finance & Compliance Engineering | March 2026 | v2 Production**

---

## The Problem

SOX compliance requires continuous monitoring of who has access to what — and flagging any single user who can both initiate and approve a financial transaction (Segregation of Duties violation). Today this is manual, slow, and only happens at audit time. By then it's too late.

---

## What We Built

An autonomous AI compliance officer that monitors all 1,932 active NetSuite users 24/7 against 18 SOD rules — detecting violations, assessing risk, and answering access questions in real time via a Slack bot and admin portal.

---

## How It Works

```
NetSuite ERP  →  Data Sync Agent  →  SOD Rule Engine  →  AI Analysis (Claude Opus 4.6)
                 (hourly + daily)     (18 rules)          Risk scoring + recommendations
                                              ↓
                             Slack Bot  ←→  Compliance team
                             MCP Server ←→  44 tools available
                             Admin Portal ←→ Angular 17 UI
```

**Three layers:**
- **Data**: Syncs user roles and permissions from NetSuite every hour (1,932 users, 99.7% coverage)
- **Analysis**: 18 SOD rules checked against every role combination; AI reasoning on CRITICAL/HIGH violations
- **Interface**: Slack bot for natural language queries; MCP server for programmatic access (44 tools); Angular admin portal

---

## Key Capabilities

| Capability | Detail |
|---|---|
| Continuous monitoring | Full sync daily at 2 AM, incremental hourly |
| Access review | "Can we give John the Controller role?" → risk verdict in <30s |
| Role recommendations | "What roles for a Revenue Manager?" → canonical answer instantly |
| Violation dashboard | Filter by severity, department, user, rule |
| Exception management | Request, route, and track SOD exceptions with Jira integration |
| Compliance reports | Executive summary, audit-ready, department-level |
| Knowledge base | Semantic search across SOX policies and compensating controls |
| Admin portal | Angular 17 UI with JWT auth, level-based access (L3–L5) |

---

## Current Status (March 2026)

| Metric | Value |
|---|---|
| Users monitored | 1,932 (99.7% of active headcount) |
| SOD rules active | 18 (Financial, Security, Compliance) |
| MCP tools available | 44 |
| Role-pair conflicts precomputed | 443 rows |
| Slack bot | Live — multi-turn agentic reasoning |
| Admin portal | Live — Angular 17 + JWT, 16 admin endpoints |
| Version | compliance-agent-v2 (production-hardened) |

---

## v2 Production Hardening (March 2026)

The system was upgraded from v1.8 to v2 with all production gaps resolved:

| Fix | Impact |
|---|---|
| NetSuite page_size 1000 → 200 | Eliminated 79.2% silent data loss on sync |
| Retry (tenacity) + circuit breaker (pybreaker) on MCP calls | Resilience to transient failures |
| Structured JSON logging (structlog + RotatingFileHandler) | Machine-readable logs, 10 MB / 5 backups |
| Bulk DB inserts via `bulk_insert_mappings` | Single commit per batch vs N individual commits |
| 4 missing DB indexes added (migration 011) | Fast queries on violations + reconciliations |
| 13 previously unreachable tools registered in tool router | All 44 tools now reachable |
| JWT exact token match in admin API | Privilege escalation vulnerability fixed |
| Silent analyzer exception return fixed | Caller can now detect DB write failures |
| Revenue Manager added to job_role_mappings | Canonical role recommendation without thin peer data |

---

## Business Value

> One SOD violation missed in a SOX audit can trigger a material weakness finding — restatement risk, increased auditor scrutiny, and remediation costs. This system eliminates that exposure continuously, not just at audit time.

**Operational impact:**
- 55× query speed improvement (on-demand → cached)
- Zero manual effort for routine access reviews
- Audit-ready evidence package available on demand
- Finance team answers role questions in Slack in <30 seconds
- 443 role-pair SOD conflicts precomputed and indexed

---

## What's Next

- Okta, Salesforce, Coupa connectors (NetSuite live today)
- Angular Portal Phase 2–4 (Audit Trail, Token Analytics, Integrations, LLM config)
- Automated Jira approval workflow routing
- Tiered approval chain (manager → Controller → CFO)
