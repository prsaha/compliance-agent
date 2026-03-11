# Quick Start Guide — compliance-agent-v2

**Version:** 2.0 | **Updated:** 2026-03-10 | **Status:** Production

This guide covers starting, verifying, and operating the **live production system**. For historical local-dev Docker setup, see the archive.

---

## Prerequisites

```bash
# Python 3.9 (system)
/Library/Developer/CommandLineTools/usr/bin/python3 --version   # 3.9.6

# PostgreSQL running with pgvector
psql $DATABASE_URL -c "SELECT extname FROM pg_extension WHERE extname='vector';"

# Redis running
redis-cli ping   # PONG

# .env configured (see Environment Variables section)
cat "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2/.env" | grep -E "DATABASE_URL|SLACK_BOT_TOKEN|ANTHROPIC"
```

---

## Startup Order

### 1. MCP Server (port 8080)

```bash
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 -m mcp.mcp_server > /tmp/mcp_server_v2.log 2>&1 &

# Verify
sleep 5
curl -s http://localhost:8080/health
# → {"status":"healthy","service":"compliance-mcp-server",...}

# Tool count check
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" -H "X-API-Key: dev-key-12345" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -c "import sys,json; t=json.load(sys.stdin)['result']['tools']; print(f'{len(t)} tools')"
# → 37 tools  (44 total including router-only tools)
```

### 2. Slack Bot

```bash
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 slack_bot_local.py > /tmp/slack_bot_v2.log 2>&1 &

# Verify — look for Socket Mode connection
sleep 8
tail -5 /tmp/slack_bot_v2.log
# → "Starting to receive messages from a new connection"
```

### 3. Verify full stack

```bash
# MCP health
curl -s http://localhost:8080/health | python3 -m json.tool

# Check processes
ps aux | grep -E "mcp\.mcp_server|slack_bot_local" | grep -v grep
```

---

## Environment Variables

All required vars in `compliance-agent-v2/.env`:

```bash
# Database
DATABASE_URL=postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# MCP
MCP_API_KEY=dev-key-12345
# MCP_SERVER_URL defaults to http://localhost:8080 (no need to set)

# NetSuite
NETSUITE_ACCOUNT_ID=...
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_RESTLET_URL=https://...

# LangSmith (optional but recommended)
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent

# Admin Portal
JWT_SECRET=<long-random-string>
ADMIN_PORTAL_PASSWORD=<portal-password>

# Feature flags
USE_MCP_CACHE=true
USE_CONV_SUMMARIES=true
USE_ANSWER_FEEDBACK=true
USE_CORRECTION_CONTEXT=true
```

---

## Quick Smoke Test

```bash
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 smoke_test_mcp_live.py
# Expected: 6/12 PASS (6 are API-drift stubs, not production issues)
# Core passing tests: DB Connection, pgvector, Data Collector, Notification Agent, Cache, Repositories
```

---

## Common Operations

### Restart MCP server
```bash
pkill -f "mcp\.mcp_server"
sleep 2
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 -m mcp.mcp_server > /tmp/mcp_server_v2.log 2>&1 &
sleep 5 && curl -s http://localhost:8080/health
```

### Restart Slack bot
```bash
pkill -f "slack_bot_local.py"
sleep 2
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2"
.venv/bin/python3 slack_bot_local.py > /tmp/slack_bot_v2.log 2>&1 &
```

### View logs (structured JSON)
```bash
tail -f /tmp/mcp_server_v2.log
tail -f /tmp/slack_bot_v2.log

# Pretty-print JSON logs
tail -f /tmp/slack_bot_v2.log | python3 -c "
import sys, json
for line in sys.stdin:
    try: d=json.loads(line); print(d.get('timestamp','')[:19], d.get('level','').upper(), d.get('event',''))
    except: print(line, end='')
"
```

### Run a DB migration
```bash
# Apply next migration
psql $DATABASE_URL -f database/migrations/011_add_performance_indexes.sql

# Rollback
psql $DATABASE_URL -f database/migrations/011_add_performance_indexes_rollback.sql
```

### Trigger a manual NetSuite sync
```bash
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" -H "X-API-Key: dev-key-12345" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"trigger_manual_sync","arguments":{"sync_type":"full"}}}'
```

### Check DB health
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users WHERE status='ACTIVE';"
psql $DATABASE_URL -c "SELECT sync_type, status, completed_at FROM sync_metadata ORDER BY started_at DESC LIMIT 3;"
psql $DATABASE_URL -c "SELECT severity, COUNT(*) FROM violations GROUP BY severity ORDER BY severity;"
```

---

## Rollback to v1

If you need to revert to the original compliance-agent:

```bash
# Kill v2 processes
pkill -f "mcp\.mcp_server"
pkill -f "slack_bot_local.py"

# Rollback new indexes (optional — indexes are safe to keep)
psql $DATABASE_URL -f "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent-v2/database/migrations/011_add_performance_indexes_rollback.sql"

# Start v1
cd "/Users/prabal.saha/Documents/ai-agent poc/compliance-agent"
.venv/bin/python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &
.venv/bin/python3 slack_bot_local.py > /tmp/slack_bot.log 2>&1 &
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| MCP server won't start | Port 8080 in use | `lsof -i :8080` then `kill <pid>` |
| Slack bot crashes immediately | Missing env var | Check `/tmp/slack_bot_v2.log` for "Missing required environment variables" |
| Circuit breaker open | MCP unreachable 5+ times | Restart MCP server; bot auto-recovers after 60s |
| `ModuleNotFoundError` | venv missing package | `cd compliance-agent-v2 && .venv/bin/pip install -r requirements.txt` |
| 0 tools in tool router | Wrong intent group | Check `utils/tool_router.py` TOOL_GROUPS |
| Slack bot reconnecting in loop | Normal Socket Mode behaviour | Ignore — it's healthy reconnection cycling |
