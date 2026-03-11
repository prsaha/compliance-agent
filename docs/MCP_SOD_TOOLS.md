# MCP Tools Reference — compliance-agent-v2

**Version:** 2.0 | **Updated:** 2026-03-10 | **Total Tools:** 44

All tools are called via `POST http://localhost:8080/mcp` with `X-API-Key: dev-key-12345`.

---

## Calling a Tool

```bash
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "analyze_access_request",
      "arguments": {
        "job_title": "Revenue Director",
        "requested_roles": ["Fivetran - Revenue Manager", "Fivetran - Revenue Approver"]
      }
    }
  }'
```

---

## Tools by Intent Group

The tool router (`utils/tool_router.py`) maps user query intent to the relevant tool subset. Claude only sees the tools relevant to the current query — this saves ~8K tokens per request.

### Access Review

| Tool | Description |
|------|-------------|
| `analyze_access_request` | Full SOD analysis for a proposed role assignment. Returns conflicts, risk score, and APPROVE/CONTROLS/REJECT recommendation. |
| `get_user_violations` | Get all open SOD violations for a user (by email or name). |
| `perform_access_review` | Formal periodic access review for a user or department. |
| `recommend_roles_for_job_title` | Canonical role recommendation for a job title. Uses `job_role_mappings` table; falls back to peer-data analysis. |
| `validate_job_role` | Check if a role is appropriate for a given job title. |
| `get_role_conflicts` | List all SOD conflicts for a specific role. |
| `check_permission_conflict` | Check if two specific permissions conflict under any SOD rule. |
| `list_all_users` | List users with optional filters (department, status, limit). |

### Violation Query

| Tool | Description |
|------|-------------|
| `get_violation_stats` | Summary statistics: violation counts by severity, status, department. |
| `list_violations` | Paginated violation list with filters: department, severity, user, rule. |
| `get_violation_details` | Full details for a specific violation ID. |
| `get_violation_history` | Violation history for a user over time. |

### Exception Management

| Tool | Description |
|------|-------------|
| `request_exception_approval` | Submit an SOD exception request for approval. |
| `check_my_approval_authority` | What violations can I approve? (Based on NetSuite authority level.) |
| `approve_exception` | Approve a pending exception (requires L4+ authority). |
| `revoke_exception` | Revoke an approved exception. |
| `get_exception_details` | Full details for a specific exception. |
| `list_active_exceptions` | All currently active (approved) exceptions. |
| `record_exception_approval` | Record a manual approval decision. |
| `find_similar_exceptions` | Find past exceptions similar to a new request (bounded to 500 rows). |
| `list_approved_exceptions` | List all historically approved exceptions. |
| `record_exception_violation` | Record when an approved exception is violated. |
| `get_exception_effectiveness_stats` | How effective have approved exceptions been? |
| `detect_exception_violations` | Scan for users violating the terms of their approved exceptions. |
| `conduct_exception_review` | Run a scheduled review of exceptions due for re-evaluation. |
| `get_exceptions_for_review` | List exceptions that are overdue for review. |

### SOD Rules

| Tool | Description |
|------|-------------|
| `query_sod_rules` | Query active SOD rules with filters (severity, category). |
| `get_sod_rule_details` | Full detail for a specific SOD rule. |
| `list_sod_rules` | List all 18 active SOD rules. |

### Knowledge Base

| Tool | Description |
|------|-------------|
| `query_knowledge_base` | Semantic search across SOX policies and compensating controls (pgvector). |
| `get_compensating_controls` | Recommended compensating controls for a violation or role conflict. |
| `get_permission_categories` | Categorised NetSuite permissions (Financial, Security, Compliance, etc.). |
| `search_permissions` | Search NetSuite permissions by keyword or category. |

### Role Analysis

| Tool | Description |
|------|-------------|
| `analyze_role_permissions` | Deep analysis of permissions in a role and their SOD implications. |
| `get_role_risk_matrix` | Query the precomputed 443-row SOD conflict matrix (cached 24h). |

### Reporting

| Tool | Description |
|------|-------------|
| `generate_compliance_report` | Full compliance report (executive summary, violation detail, remediation plan). |
| `get_org_risk_assessment` | Organisation-wide risk assessment with department breakdown. |
| `export_report` | Export a report in PDF/CSV/JSON format. |
| `generate_violation_report` | Violation-focused report for audit purposes. |

### System

| Tool | Description |
|------|-------------|
| `list_systems` | List connected systems and their sync status. |
| `get_system_status` | Detailed health of all integrated systems. |
| `trigger_manual_sync` | Trigger a full or incremental NetSuite sync. |
| `get_sync_status` | Status of the last sync run. |
| `initialize_session` | Set the current user's context (email → authority level). |
| `start_collection_agent` | Start the background data collection agent. |
| `stop_collection_agent` | Stop the background data collection agent. |
| `get_collection_agent_status` | Is the collection agent running? Last run time? |

### Remediation

| Tool | Description |
|------|-------------|
| `remediate_violation` | Mark a violation as remediated and record the action taken. |
| `schedule_review` | Schedule a future access review for a user or role. |
| `create_remediation_ticket` | Create a Jira ticket for a violation. |
| `notify_manager` | Send a Slack/email notification to a user's manager. |

---

## Key Tools — Detailed Reference

### `analyze_access_request`

The most-used tool. Performs full SOD analysis for a proposed role assignment.

**Parameters:**
```json
{
  "job_title": "Revenue Director",
  "requested_roles": ["Fivetran - Revenue Manager"],
  "user_email": "john@fivetran.com"   // optional — enriches with current roles
}
```

**Returns:** conflict list, risk score (CRITICAL/HIGH/MEDIUM/LOW), APPROVE/CONTROLS/REJECT verdict, compensating controls.

**Performance:** ~2–5s (calls Claude Opus 4.6)

---

### `recommend_roles_for_job_title`

Returns canonical role recommendations for a job title.

**Parameters:**
```json
{
  "job_title": "Revenue Manager",
  "department": "Finance"   // optional
}
```

**Logic:**
1. If `job_role_mappings` table has a canonical mapping → returns "Assign these roles: X, Y" directly
2. If peer data available (≥2 peers with roles) → uses peer-based recommendation
3. Falls back to general guidance

**Performance:** <200ms (DB lookup)

---

### `get_role_risk_matrix`

Queries the precomputed 443-row conflict matrix for all 35 Fivetran roles.

**Parameters:**
```json
{
  "role_name": "Fivetran - Controller",  // optional filter
  "severity": "CRITICAL",               // optional filter
  "intra_role": true                     // check within-role conflicts
}
```

**Cached:** 24 hours in Redis. **Response limit:** 3 bullets, max 1,200 chars.

---

### `list_violations`

Paginated violation list with filters.

**Parameters:**
```json
{
  "department": "Finance",
  "severity": "HIGH",
  "user_email": "jane@fivetran.com",
  "status": "OPEN",
  "limit": 20,
  "offset": 0
}
```

---

## Registering New Tools

1. Add handler `async def my_tool_handler(...)` to `mcp/mcp_tools.py`
2. Add to `TOOL_HANDLERS` dict in `mcp/mcp_tools.py`
3. Register in `utils/tool_router.py` under the appropriate intent group
4. Add re-export to `mcp/tools/<phase>_tools.py`
5. Restart MCP server and verify:

```bash
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" -H "X-API-Key: dev-key-12345" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -c "import sys,json; tools=json.load(sys.stdin)['result']['tools']; [print(t['name']) for t in tools]"
```

---

## Performance Reference

| Tool | Typical Latency | Cache |
|------|----------------|-------|
| `analyze_access_request` | 2–5s | 1h Redis |
| `get_user_violations` | <200ms | 1h Redis |
| `get_role_conflicts` | <100ms | 24h Redis |
| `get_role_risk_matrix` | <100ms | 24h Redis |
| `get_violation_stats` | <200ms | 30min Redis |
| `list_violations` | <300ms | none |
| `trigger_manual_sync` | async | no cache |
| `query_knowledge_base` | 500ms–2s | 1h Redis |

---

**Last Updated:** 2026-03-10
