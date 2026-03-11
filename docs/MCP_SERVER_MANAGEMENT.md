# MCP Server Management Guide

**Version:** 2.0 | **Updated:** 2026-03-10 | **Status:** Production

---

## Quick Reference

```bash
# ── Start ─────────────────────────────────────────────────────────
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 -m mcp.mcp_server > /tmp/mcp_server_v2.log 2>&1 &

# ── Verify ────────────────────────────────────────────────────────
sleep 5 && curl -s http://localhost:8080/health | python3 -m json.tool

# ── Tool count ────────────────────────────────────────────────────
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" -H "X-API-Key: dev-key-12345" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -c "import sys,json; t=json.load(sys.stdin)['result']['tools']; print(f'{len(t)} tools')"
# → 37 tools  (44 total; 7 are router-only, not in schema list)

# ── Stop ──────────────────────────────────────────────────────────
pkill -f "mcp\.mcp_server"

# ── Restart (one-liner) ───────────────────────────────────────────
pkill -f "mcp\.mcp_server"; sleep 2; \
  cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"; \
  .venv/bin/python3 -m mcp.mcp_server > /tmp/mcp_server_v2.log 2>&1 &

# ── Logs ──────────────────────────────────────────────────────────
tail -f /tmp/mcp_server_v2.log
```

---

## Server Operations

### Starting

Always use the project's own venv — system Python breaks TLS (certifi path is wrong):

```bash
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 -m mcp.mcp_server > /tmp/mcp_server_v2.log 2>&1 &
```

Verify startup (wait ~5s for uvicorn to bind):
```bash
sleep 5
curl -s http://localhost:8080/health
# → {"status":"healthy","service":"compliance-mcp-server","tools":37,...}
```

### Stopping

```bash
pkill -f "mcp\.mcp_server"
# Force kill if unresponsive:
pkill -9 -f "mcp\.mcp_server"
```

### Full Restart

```bash
pkill -f "mcp\.mcp_server"
sleep 2
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 -m mcp.mcp_server > /tmp/mcp_server_v2.log 2>&1 &
sleep 5 && curl -s http://localhost:8080/health
```

---

## Monitoring & Health Checks

### Process check

```bash
ps aux | grep -E "mcp\.mcp_server" | grep -v grep
```

### Port check

```bash
lsof -i :8080 | grep LISTEN
```

### View logs (JSON structured)

```bash
# Raw JSON logs
tail -f /tmp/mcp_server_v2.log

# Pretty-printed (timestamp + level + event)
tail -f /tmp/mcp_server_v2.log | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        print(d.get('timestamp','')[:19], d.get('level','').upper(), d.get('event',''))
    except:
        print(line, end='')
"

# Errors only
tail -f /tmp/mcp_server_v2.log | grep -i '"level":"error"'
```

Logs rotate automatically: 10 MB max, 5 backups (configured in `slack_bot_local.py`).

### Database stats

```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users WHERE status='ACTIVE';"
psql $DATABASE_URL -c "SELECT sync_type, status, completed_at FROM sync_metadata ORDER BY started_at DESC LIMIT 3;"
psql $DATABASE_URL -c "SELECT severity, COUNT(*) FROM violations GROUP BY severity ORDER BY severity;"
```

---

## Tool Management

### List all tools

```bash
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" -H "X-API-Key: dev-key-12345" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -m json.tool | grep '"name"'
```

### Call a tool directly

```bash
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" -H "X-API-Key: dev-key-12345" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_systems","arguments":{}}}' \
  | python3 -m json.tool
```

### Trigger a manual NetSuite sync

```bash
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" -H "X-API-Key: dev-key-12345" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"trigger_manual_sync","arguments":{"sync_type":"full"}}}'
```

### Adding a new tool

1. Add handler in `mcp/mcp_tools.py`
2. Register in `utils/tool_router.py` (add to the matching intent group)
3. Add re-export in `mcp/tools/<phase>_tools.py`
4. Restart MCP server

---

## Configuration

### Environment variables

See `.env` for all vars. Key ones for MCP server:

```bash
DATABASE_URL=postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
MCP_API_KEY=dev-key-12345
NETSUITE_ACCOUNT_ID=...
# Feature flags
USE_MCP_CACHE=true
USE_CONV_SUMMARIES=true
```

After changing `.env`, restart the server.

### Port

Default is 8080. To change: edit `mcp/mcp_server.py` uvicorn call and update any clients.

---

## Database Migrations

```bash
# Apply a migration
psql $DATABASE_URL -f database/migrations/011_add_performance_indexes.sql

# Rollback
psql $DATABASE_URL -f database/migrations/011_add_performance_indexes_rollback.sql

# Check current indexes
psql $DATABASE_URL -c "\d violations"
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Port 8080 already in use | Old process still running | `lsof -i :8080` then `kill <pid>` |
| `ModuleNotFoundError` | Wrong Python / venv not activated | Use `.venv/bin/python3`, not system `python3` |
| 0 tools returned | Tool not registered in `tool_router.py` | Add to appropriate intent group |
| `{"error": "Unauthorized"}` | Wrong API key | Use `X-API-Key: dev-key-12345` |
| Server starts but crashes after 10s | Missing env var or DB unreachable | Check `/tmp/mcp_server_v2.log` |
| NetSuite sync gets < 200 users | page_size misconfigured | Verify `page_size=200` in `netsuite_client.py:144` |

### Server won't start — diagnostics

```bash
# Run in foreground to see all errors
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 -m mcp.mcp_server

# Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check port conflicts
lsof -i :8080
```

---

## Rollback to v1

```bash
# Kill v2
pkill -f "mcp\.mcp_server"

# Optional: rollback new indexes
psql $DATABASE_URL -f "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2/database/migrations/011_add_performance_indexes_rollback.sql"

# Start v1
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent"
.venv/bin/python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &
```

---

## Log Files

| Log | Path |
|-----|------|
| MCP server (v2) | `/tmp/mcp_server_v2.log` |
| Slack bot (v2) | `/tmp/slack_bot_v2.log` |
| MCP server (v1) | `/tmp/mcp_server.log` |
| Slack bot (v1) | `/tmp/slack_bot.log` |

All logs are structured JSON (structlog). Use the pretty-printer above for human-readable output.

---

**Last Updated:** 2026-03-10
