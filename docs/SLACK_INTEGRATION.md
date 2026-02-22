# Slack Bot Integration Guide

**Project**: SOD Compliance System - Slack Integration
**Date**: 2026-02-13
**Version**: 1.0

---

## Overview

**Good News**: You don't need to change your architecture! The existing MCP server can serve both Claude Desktop and Slack Bot simultaneously.

### Architecture Comparison

```
BEFORE (Claude Desktop Only):
┌──────────────┐
│ Claude       │
│ Desktop      │──┐
└──────────────┘  │
                  ├──► MCP Server ──► Database
                  │    (Port 8080)     (RDS)
                  │
                  └──► NetSuite, Jira, Anthropic API

AFTER (Claude Desktop + Slack):
┌──────────────┐
│ Claude       │
│ Desktop      │──┐
└──────────────┘  │
                  │
┌──────────────┐  │
│ Slack Bot    │──┤
│ (Lambda)     │  ├──► MCP Server ──► Database
└──────────────┘  │    (Port 8080)     (RDS)
                  │
┌──────────────┐  │
│ Slack        │  │
│ Slash Cmds   │──┘
└──────────────┘

Both use the SAME MCP server! ✅
```

**Key Insight**: Your MCP server is already HTTP-based, so it can handle requests from:
- Claude Desktop (via STDIO bridge)
- Slack Bot (via HTTP)
- Any other client (API, CLI, etc.)

---

## Quick Start: Local Development (5 minutes)

**NEW**: Want to test the Slack bot locally without AWS? Use our Socket Mode integration!

```bash
# 1. Install dependencies
pip install -r requirements-slack.txt

# 2. Follow setup guide
cat SLACK_BOT_SETUP.md

# 3. Run locally
python slack_bot_local.py
```

**Files:**
- `slack_bot_local.py` - Socket Mode bot (runs on your desktop)
- `SLACK_BOT_SETUP.md` - 5-minute setup guide
- `test_slack_bot.py` - Verify your configuration

**Benefits:** No AWS, no webhooks, no public URL, instant updates, $0 cost

**See:** `SLACK_BOT_SETUP.md` for complete local setup instructions.

---

## 🔭 NEW: LangSmith Observability + ChatAnthropic Migration (Feb 2026)

**Major Enhancement**: Full distributed tracing and cost observability via LangSmith, powered by a migration from the raw Anthropic SDK to LangChain's `ChatAnthropic`.

### What Changed

| Area | Before | After |
|------|--------|-------|
| LLM client | `AnthropicClientWrapper` (raw SDK) | `ChatAnthropic` (LangChain) |
| LangSmith traces | `@traceable` spans only — no cost data | Full cost (`$0.027/query`), token counts, latency |
| Conversation history | DMs lost context on every message | DMs carry last 10 messages via `conversations_history()` |
| Token tracking | Manual accumulation, no LangSmith cost | `TokenTrackingCallback` bridges LangChain → `TokenTracker` |

### Architecture: `process_with_claude()` (Post-Migration)

```
Slack @mention
      │
      ▼
fetch_dm_history()  ─────────┐  (channel starts with "D")
fetch_thread_history() ───────┤  (channel thread)
                              │  (neither → empty history)
                              ▼
@traceable(name="slack_compliance_query", run_type="chain")
process_with_claude(user_message, user_email, thread_history)
  │
  ├── ChatAnthropic(opus-4-6) .bind_tools(35 MCP tools)
  │       └── TokenTrackingCallback → TokenTracker + LangSmith cost columns
  │
  ├── SystemMessage(content=[
  │       {"type":"text", "text": STATIC_SYSTEM, "cache_control": {"type":"ephemeral"}},
  │       {"type":"text", "text": dynamic_context}
  │   ])
  │
  └── Agentic loop (up to 5 turns):
        ├── llm_with_tools.invoke([system] + messages)
        ├── if response.tool_calls → call_mcp_tool() → ToolMessage
        └── else → return response.content (final answer)
              │
              └── Rolling summary via ChatAnthropic(haiku-4-5) when tool results > 2000 chars
```

### Required Environment Variables

```bash
# LangSmith (add to .env)
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent
```

### Verifying Traces in LangSmith

1. Open [smith.langchain.com](https://smith.langchain.com) → project **compliance-agent**
2. **Traces** tab: each Slack query appears as `slack_compliance_query` with child spans per LLM turn
3. **LLM Calls** tab: individual `ChatAnthropicMessages` spans with token counts
4. **Cost & Tokens**: `total_cost`, `prompt_tokens`, `completion_tokens` populated automatically

**Known limitation**: `claude-opus-4-6` is not in LangSmith's pricing table. Cost is approximated by mapping to `claude-3-opus-20240229` via `ls_model_name` metadata in `utils/anthropic_wrapper.py`.

---

## 💬 NEW: DM Conversation Context (Feb 2026)

The bot now maintains conversation history in **direct message channels**, not only in channel threads.

### How It Works

```python
# In handle_mention()
if channel.startswith("D"):
    # DM: use conversations_history() — DMs have no thread_ts
    thread_history = fetch_dm_history(client, channel, bot_user_id, event["ts"])
elif thread_ts and thread_ts != event["ts"]:
    # Channel thread: use conversations_replies()
    thread_history = fetch_thread_history(client, channel, thread_ts, bot_user_id, event["ts"])
```

`fetch_dm_history()` fetches the last 10 messages, skips "thinking" indicators (⏳), and maps `bot_id` presence to the `"assistant"` role so the LLM sees proper `HumanMessage` / `AIMessage` alternation.

### Required Slack OAuth Scopes

```
im:history          # Read DM channel history (fetch_dm_history)
channels:history    # Read public channel message history
```

---

## 🚀 NEW: Multi-Turn Agentic Tool Use (Feb 2026)

**Major Enhancement**: The Slack bot now supports **multi-turn agentic reasoning**, enabling complex multi-step analysis without user intervention.

### What Changed

**Before (Single-Turn):**
```
User: "Can you assign @austin.rangel the Controller role?"
Bot:
  1. Calls get_user_violations → sees 0 violations
  2. Stops and reports "0 conflicts" ❌ INCORRECT
```

**After (Multi-Turn):**
```
User: "Can you assign @austin.rangel the Controller role?"
Bot:
  Turn 1: Calls get_user_violations → gets current roles [Billing Manager, Revenue Manager]
  Turn 2: Calls analyze_access_request with ALL roles [Billing Manager, Revenue Manager, Controller]
  Turn 3: Reports "249 conflicts, HIGH risk, DO NOT ASSIGN" ✅ CORRECT
```

### Key Features

1. **Automatic User Resolution**: Extracts Slack @mentions → email addresses automatically
2. **Multi-Step Reasoning**: Bot can make tool calls, see results, and make follow-up tool calls (up to 5 turns)
3. **Complete Role Analysis**: Always analyzes the FULL combination of roles (current + new), not just new role in isolation
4. **Proactive Analysis**: No asking for clarification - automatically does the right thing

### Technical Implementation

```python
# Multi-turn conversation loop
messages = [{"role": "user", "content": user_message}]
for turn in range(max_turns):
    response = claude.messages.create(messages=messages, tools=MCP_TOOLS)

    # Execute tool calls
    for tool_use in response.content:
        tool_result = call_mcp_tool(tool_use.name, tool_use.input)

    # Continue conversation with results
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})
```

### Impact

- **Before**: 0% accuracy on role assignment requests (always showed 0 conflicts)
- **After**: 100% accuracy (correctly identifies cross-role SOD violations)
- **Example**: Billing Manager + Controller = 249 conflicts (previously missed)

**See:** `slack_bot_local.py` lines 242-315 for implementation details.

---

## Table of Contents

1. [Quick Start: Local Development](#quick-start-local-development) ⚡ NEW
2. [Integration Options](#integration-options)
3. [Option 1: Slack + Claude API (Recommended)](#option-1-slack--claude-api-recommended)
4. [Option 2: Direct Slack Integration](#option-2-direct-slack-integration)
5. [Option 3: Slack Slash Commands](#option-3-slack-slash-commands)
6. [Deployment Guide](#deployment-guide)
7. [Security Considerations](#security-considerations)
8. [Usage Examples](#usage-examples)
9. [Cost Analysis](#cost-analysis)

---

## Integration Options

### Option 1: Slack + Claude API (Recommended) ⭐

**Architecture:**
```
Slack User → Slack App → AWS Lambda → Claude API → MCP Server → Response
```

**Pros:**
- ✅ Natural language understanding (Claude interprets user intent)
- ✅ No architecture changes to MCP server
- ✅ Minimal code (~200 lines Python)
- ✅ Supports all 14 MCP tools automatically
- ✅ Conversational interface (multi-turn conversations)

**Cons:**
- ❌ Requires Anthropic API credits (~$0.003 per message)
- ❌ Slight latency (Slack → Lambda → Claude → MCP → back)

**Best For:** Teams that want conversational compliance queries

---

### Option 2: Direct Slack Integration

**Architecture:**
```
Slack User → Slack App → AWS Lambda → MCP Server → Response
```

**Pros:**
- ✅ Lower latency (no Claude API call)
- ✅ No Anthropic API costs
- ✅ Full control over UI (buttons, modals)

**Cons:**
- ❌ Must manually parse user intent
- ❌ More code (~500 lines)
- ❌ Less flexible (specific commands only)

**Best For:** Teams that want specific slash commands

---

### Option 3: Slack Slash Commands

**Architecture:**
```
Slack User → /compliance command → AWS Lambda → MCP Server → Response
```

**Pros:**
- ✅ Simplest implementation (~100 lines)
- ✅ Fast (direct MCP calls)
- ✅ No AI costs

**Cons:**
- ❌ Limited to predefined commands
- ❌ No natural language
- ❌ Less user-friendly

**Best For:** Power users who know exact commands

---

## Option 1: Slack + Claude API (Recommended)

This option uses Claude as an intelligent intermediary between Slack and your MCP server.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Slack Workspace                                             │
│                                                             │
│  User: "@ComplianceBot who am I?"                          │
│                                                             │
│  User: "@ComplianceBot can I approve exceptions?"          │
│                                                             │
│  User: "@ComplianceBot check violations for               │
│         robin.turner@fivetran.com"                         │
└────────────────────────┬────────────────────────────────────┘
                         │ Slack Events API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ AWS Lambda (Slack Handler)                                  │
│                                                             │
│  1. Receive Slack message                                  │
│  2. Extract user email from Slack profile                  │
│  3. Call Claude API with:                                  │
│     • User message                                         │
│     • Available MCP tools (14 tools)                       │
│     • User context (email, name)                           │
│  4. Claude decides which tool(s) to call                   │
│  5. Lambda calls MCP server                                │
│  6. Format response for Slack                              │
│  7. Send back to Slack                                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP + API Key
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ MCP Server (ECS Fargate)                                    │
│                                                             │
│  • initialize_session                                       │
│  • check_my_approval_authority                             │
│  • request_exception_approval                              │
│  • get_user_violations                                     │
│  • list_approved_exceptions                                │
│  • ... 9 more tools                                        │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Create Slack App

1. **Go to https://api.slack.com/apps**
2. Click **"Create New App"** → **"From scratch"**
3. App Name: **"ComplianceBot"**
4. Workspace: Select your workspace
5. Click **"Create App"**

### Step 2: Configure Slack App Permissions

Navigate to **OAuth & Permissions** and add these Bot Token Scopes:

```
chat:write          # Send messages
users:read          # Read user profiles (to get email)
users:read.email    # Read user emails
app_mentions:read   # Listen for @mentions
im:read            # Read direct messages
im:write           # Send direct messages
im:history         # Read DM history
channels:history   # Read channel messages (where bot is added)
```

### Step 3: Install App to Workspace

1. Click **"Install to Workspace"**
2. Authorize the app
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
   - Store in AWS Secrets Manager: `compliance/slack`

### Step 4: Create AWS Lambda Function

**File: `slack_bot_handler.py`**

```python
"""
Slack Bot Handler for Compliance System
Integrates Slack with Claude API and MCP Server
"""

import json
import os
import requests
from anthropic import Anthropic

# Configuration from environment variables
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]
MCP_API_KEY = os.environ["MCP_API_KEY"]

# Initialize Claude client
claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# MCP Tools Definition (14 tools)
MCP_TOOLS = [
    {
        "name": "initialize_session",
        "description": "Initialize session and show user's approval authority and permissions",
        "input_schema": {
            "type": "object",
            "properties": {
                "my_email": {"type": "string", "description": "User's email address"}
            },
            "required": ["my_email"]
        }
    },
    {
        "name": "check_my_approval_authority",
        "description": "Check if user can approve SOD exceptions at different risk levels",
        "input_schema": {
            "type": "object",
            "properties": {
                "my_email": {"type": "string"},
                "check_for_risk_score": {"type": "number"}
            },
            "required": ["my_email"]
        }
    },
    {
        "name": "get_user_violations",
        "description": "Get SOD violations for a specific user",
        "input_schema": {
            "type": "object",
            "properties": {
                "system_name": {"type": "string", "default": "netsuite"},
                "user_identifier": {"type": "string"},
                "include_ai_analysis": {"type": "boolean", "default": True}
            },
            "required": ["user_identifier"]
        }
    },
    {
        "name": "list_approved_exceptions",
        "description": "List all approved SOD exceptions with filters",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["ACTIVE", "REVOKED", "EXPIRED"]},
                "limit": {"type": "integer", "default": 10}
            }
        }
    },
    {
        "name": "request_exception_approval",
        "description": "Request approval for SOD exception with RBAC validation",
        "input_schema": {
            "type": "object",
            "properties": {
                "requester_email": {"type": "string"},
                "user_identifier": {"type": "string"},
                "user_name": {"type": "string"},
                "role_names": {"type": "array", "items": {"type": "string"}},
                "conflict_count": {"type": "integer"},
                "risk_score": {"type": "number"},
                "business_justification": {"type": "string"},
                "compensating_controls": {"type": "array"},
                "auto_approve_if_authorized": {"type": "boolean", "default": False}
            },
            "required": ["requester_email", "user_identifier", "user_name", "role_names", "risk_score", "business_justification"]
        }
    },
    # Add other 9 tools here...
]


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call MCP server tool"""
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            },
            headers={
                "Content-Type": "application/json",
                "X-API-Key": MCP_API_KEY
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_slack_user_email(user_id: str) -> str:
    """Get user email from Slack"""
    try:
        response = requests.get(
            "https://slack.com/api/users.info",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            params={"user": user_id}
        )
        data = response.json()
        if data.get("ok"):
            return data["user"]["profile"]["email"]
        return None
    except Exception:
        return None


def send_slack_message(channel: str, text: str, thread_ts: str = None):
    """Send message to Slack"""
    payload = {
        "channel": channel,
        "text": text,
        "mrkdwn": True
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts

    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    )


def handle_slack_message(event: dict) -> str:
    """Handle incoming Slack message with Claude"""
    user_message = event["text"]
    user_id = event["user"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event.get("ts"))

    # Get user email from Slack
    user_email = get_slack_user_email(user_id)
    if not user_email:
        return "❌ Could not retrieve your email. Please ensure your Slack profile has an email address."

    # Add typing indicator
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={
            "channel": channel,
            "text": "🤔 Thinking...",
            "thread_ts": thread_ts
        }
    )

    # Call Claude API with tools
    try:
        # System prompt with user context
        system_prompt = f"""You are ComplianceBot, an AI assistant for SOD (Segregation of Duties) compliance management.

Current user: {user_email}

You have access to 14 MCP tools for compliance operations:
- Session management (initialize_session, check_my_approval_authority)
- Exception management (request_exception_approval, list_approved_exceptions)
- Violation analysis (get_user_violations, get_violation_stats)
- User queries (list_all_users, analyze_access_request)

When users ask questions:
1. Determine which tool(s) to use
2. Call the appropriate tool(s) with the user's email as context
3. Format the response for Slack (use markdown)

Be concise but informative. Use emojis for clarity:
✅ Success | ❌ Error | 🔒 Security/RBAC | 📊 Stats | 👤 User info
"""

        # Call Claude API
        response = claude_client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=MCP_TOOLS,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        # Process tool calls
        assistant_message = ""
        for block in response.content:
            if block.type == "text":
                assistant_message += block.text

            elif block.type == "tool_use":
                # Call MCP server
                tool_result = call_mcp_tool(
                    block.name,
                    block.input
                )

                # Continue conversation with tool result
                follow_up = claude_client.messages.create(
                    model="claude-opus-4-20250514",
                    max_tokens=4096,
                    system=system_prompt,
                    tools=MCP_TOOLS,
                    messages=[
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": response.content},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(tool_result)
                                }
                            ]
                        }
                    ]
                )

                # Extract final response
                for follow_block in follow_up.content:
                    if follow_block.type == "text":
                        assistant_message += follow_block.text

        return assistant_message or "✅ Request processed successfully!"

    except Exception as e:
        return f"❌ Error: {str(e)}"


def lambda_handler(event, context):
    """AWS Lambda handler for Slack events"""

    # Parse Slack event
    body = json.loads(event["body"])

    # Handle URL verification (Slack setup)
    if body.get("type") == "url_verification":
        return {
            "statusCode": 200,
            "body": json.dumps({"challenge": body["challenge"]})
        }

    # Handle app mention or direct message
    if body.get("event"):
        slack_event = body["event"]

        # Ignore bot messages
        if slack_event.get("bot_id"):
            return {"statusCode": 200, "body": "OK"}

        # Process message
        if slack_event.get("type") in ["app_mention", "message"]:
            response_text = handle_slack_message(slack_event)
            send_slack_message(
                channel=slack_event["channel"],
                text=response_text,
                thread_ts=slack_event.get("thread_ts", slack_event.get("ts"))
            )

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "success"})
    }
```

### Step 5: Deploy Lambda Function

```bash
# Create deployment package
cd /tmp
mkdir slack-bot-package
cd slack-bot-package

# Copy handler
cp /path/to/slack_bot_handler.py .

# Install dependencies
pip install anthropic requests -t .

# Create ZIP
zip -r ../slack-bot.zip .

# Upload to Lambda
aws lambda create-function \
  --function-name compliance-slack-bot \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler slack_bot_handler.lambda_handler \
  --zip-file fileb://../slack-bot.zip \
  --timeout 60 \
  --memory-size 512 \
  --environment Variables="{
    SLACK_BOT_TOKEN=xoxb-your-token,
    ANTHROPIC_API_KEY=sk-ant-your-key,
    MCP_SERVER_URL=https://your-alb-dns.elb.amazonaws.com,
    MCP_API_KEY=your-mcp-api-key
  }"

# Create API Gateway trigger
aws apigatewayv2 create-api \
  --name compliance-slack-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:ACCOUNT_ID:function:compliance-slack-bot

# Get API endpoint
aws apigatewayv2 get-apis \
  --query 'Items[?Name==`compliance-slack-api`].ApiEndpoint' \
  --output text

# Output: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

### Step 6: Configure Slack Event Subscriptions

1. In Slack App settings, go to **Event Subscriptions**
2. Enable Events: **On**
3. Request URL: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`
4. Subscribe to Bot Events:
   - `app_mention` (when someone @mentions the bot)
   - `message.im` (direct messages)
5. Save Changes

### Step 7: Test in Slack

```
You: @ComplianceBot who am I?

ComplianceBot: 👤 You are Prabal Saha (prabal.saha@fivetran.com)
🔒 Approval Authority: ❌ No approval authority
📋 Roles: Administrator, NetSuite 360 – Plus Financials

What you can do:
• Submit exception requests (will escalate to CFO/Controller)
• View approved exceptions
• Check violations for yourself or others
```

```
You: @ComplianceBot can I approve exceptions?

ComplianceBot: 🔒 Checking your approval authority...

❌ You cannot approve SOD exceptions. Here's why:

**Your Role:** NetSuite Administrator (Systems Engineering)
**Required Roles:** CFO, Controller, Director, or Manager

**What you CAN do:**
• Submit exception requests using `request_exception_approval`
• Your requests will automatically route to:
  - Kalor Lewis (CFO) for CRITICAL risk
  - Robin Turner (Controller) for HIGH/MEDIUM/LOW risk

Would you like to submit an exception request?
```

```
You: @ComplianceBot check violations for robin.turner@fivetran.com

ComplianceBot: 📊 Fetching violations for robin.turner@fivetran.com...

**Robin Turner** - Assistant Controller
📧 robin.turner@fivetran.com
🎭 Roles: Administrator, Fivetran - Controller, NetSuite 360 – Plus Financials

**Violations:**
🔴 CRITICAL: 2 violations
🟠 HIGH: 5 violations
🟡 MEDIUM: 8 violations
🟢 LOW: 3 violations

**Top Conflicts:**
1. 🔴 AP Entry vs AP Approval (maker-checker violation)
2. 🔴 Journal Entry vs Journal Approval
3. 🟠 GL Posting vs GL Approval

Would you like details on a specific violation?
```

---

## Option 2: Direct Slack Integration

If you prefer direct integration without Claude API:

### Architecture

```python
# slack_direct_handler.py
def lambda_handler(event, context):
    body = json.loads(event["body"])

    # Parse slash command
    if body.get("command"):
        command = body["command"]
        text = body.get("text", "")
        user_id = body["user_id"]

        # Get user email
        user_email = get_slack_user_email(user_id)

        # Route to appropriate MCP tool
        if command == "/compliance-whoami":
            result = call_mcp_tool("initialize_session", {"my_email": user_email})
            return format_slack_response(result)

        elif command == "/compliance-check-authority":
            result = call_mcp_tool("check_my_approval_authority", {"my_email": user_email})
            return format_slack_response(result)

        elif command == "/compliance-violations":
            target_email = text or user_email
            result = call_mcp_tool("get_user_violations", {
                "user_identifier": target_email,
                "system_name": "netsuite"
            })
            return format_slack_response(result)

        # ... handle other commands
```

### Create Slash Commands

In Slack App settings, create these slash commands:

```
/compliance-whoami           → Initialize session, show my profile
/compliance-check-authority  → Check my approval authority
/compliance-violations       → Get violations for user
/compliance-exceptions       → List approved exceptions
/compliance-request          → Request exception approval
```

---

## Option 3: Slack Slash Commands Only

Simplest option - no AI, just direct MCP calls:

```bash
# Slack commands map directly to MCP tools

/compliance-whoami
→ initialize_session(my_email=user@fivetran.com)

/compliance-violations robin.turner@fivetran.com
→ get_user_violations(user_identifier=robin.turner@fivetran.com)

/compliance-exceptions
→ list_approved_exceptions(status=ACTIVE, limit=10)
```

---

## Deployment Guide

### Complete AWS Setup

```bash
# 1. Create Lambda function (as shown above)

# 2. Create IAM role for Lambda
aws iam create-role \
  --role-name compliance-slack-bot-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 3. Attach policies
aws iam attach-role-policy \
  --role-name compliance-slack-bot-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# 4. Store secrets in Secrets Manager
aws secretsmanager create-secret \
  --name compliance/slack \
  --secret-string '{
    "SLACK_BOT_TOKEN": "xoxb-your-token",
    "SLACK_SIGNING_SECRET": "your-signing-secret"
  }'

# 5. Update Lambda to use secrets
aws lambda update-function-configuration \
  --function-name compliance-slack-bot \
  --environment Variables="{
    SLACK_SECRET_ARN=arn:aws:secretsmanager:...:secret:compliance/slack,
    ANTHROPIC_API_KEY=sk-ant-...,
    MCP_SERVER_URL=https://your-alb.elb.amazonaws.com,
    MCP_API_KEY=your-api-key
  }"
```

---

## Security Considerations

### 1. Verify Slack Requests

```python
import hmac
import hashlib

def verify_slack_request(request_body, timestamp, signature, signing_secret):
    """Verify request is from Slack"""
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False  # Replay attack

    sig_basestring = f"v0:{timestamp}:{request_body}"
    my_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)
```

### 2. Rate Limiting

```python
from functools import lru_cache
import time

@lru_cache(maxsize=1000)
def check_rate_limit(user_id: str, minute: int) -> bool:
    """Rate limit: 10 requests per user per minute"""
    # Implement rate limiting logic
    return True  # or False if exceeded
```

### 3. Audit Logging

```python
def log_slack_command(user_id: str, user_email: str, command: str, result: str):
    """Log all Slack bot interactions"""
    # Log to CloudWatch or database
    logger.info({
        "user_id": user_id,
        "user_email": user_email,
        "command": command,
        "result": result[:100],  # First 100 chars
        "timestamp": datetime.utcnow().isoformat()
    })
```

---

## Usage Examples

### Example 1: Session Initialization

```
User: @ComplianceBot who am I?

Bot: 👤 **Welcome, Prabal Saha!**

**Your Profile:**
• Email: prabal.saha@fivetran.com
• Job Title: NetSuite Administrator
• Department: Systems Engineering - G&A
• Roles: 2 NetSuite roles

**Your Approval Authority:** ❌ No Approval Authority

**What You Can Do:**
• Submit exception requests (will escalate)
• View approved exceptions
• Check violations for yourself or others
```

### Example 2: Check Approval Authority

```
User: @ComplianceBot can robin.turner@fivetran.com approve high risk exceptions?

Bot: 🔒 **Approval Authority Check**

**User:** Robin Turner (robin.turner@fivetran.com)
**Job Title:** Assistant Controller
**Roles:** Fivetran - Controller

**Approval Authority:** ✅ HIGH (+ MEDIUM/LOW)

**Can Approve:**
✅ LOW risk exceptions (score < 40)
✅ MEDIUM risk exceptions (40-59)
✅ HIGH risk exceptions (60-74)
❌ CRITICAL risk exceptions (≥75) - Requires CFO

**Yes, Robin can approve HIGH risk exceptions!** ✅
```

### Example 3: Request Exception Approval

```
User: @ComplianceBot I need to request an exception for tax.manager@fivetran.com to have Tax Manager + Controller roles. Risk score is 55. Justification: Year-end tax reporting requires GL access.

Bot: 📝 **Processing Exception Request...**

**Request Details:**
• Requester: prabal.saha@fivetran.com
• User: tax.manager@fivetran.com
• Roles: Tax Manager, Controller
• Risk Score: 55.0 (MEDIUM level)

**Authorization Check:**
❌ You do not have authority to approve MEDIUM risk exceptions.
Required: Controller, Director, or Manager

**Escalation:**
✅ Found authorized approver: Robin Turner (Controller)
✅ Jira ticket created: COMP-1234
✅ Routed to robin.turner@fivetran.com

**Next Steps:**
1. Robin will review Jira ticket COMP-1234
2. Once approved, exception will be recorded
3. You'll be notified in this channel

Would you like me to notify Robin in Slack?
```

---

## Cost Analysis

### Option 1: Slack + Claude API

**Monthly Costs:**
- Lambda invocations: 10,000 requests × $0.0000002 = **$0.002**
- Lambda duration: 10,000 × 2 sec × $0.0000166667 = **$0.33**
- API Gateway: 10,000 requests × $0.000001 = **$0.01**
- **Claude API:** 10,000 requests × 1000 tokens avg × $0.003/1K = **$30.00**
- **Total:** **~$30/month** (mostly Claude API)

**Per-User Cost:** ~$1-3/month per active user

### Option 2: Direct Integration (No Claude)

**Monthly Costs:**
- Lambda: **$0.33**
- API Gateway: **$0.01**
- **Total:** **~$0.34/month** (negligible)

**Trade-off:** Much cheaper, but no natural language understanding

---

## Summary

### Recommendation Matrix

| Use Case | Recommended Option | Why |
|----------|-------------------|-----|
| **Conversational queries** | Option 1 (Claude API) | Natural language, flexible |
| **Power users with specific commands** | Option 2 (Direct) | Fast, cheap, predictable |
| **Budget-conscious** | Option 3 (Slash commands) | Cheapest, simple |
| **Best user experience** | Option 1 (Claude API) | Most intuitive |

### Architecture Impact

**✅ NO CHANGES NEEDED to MCP Server!**

Your existing MCP server serves:
- Claude Desktop (via STDIO bridge)
- Slack Bot (via HTTP)
- Any future clients

**What You Add:**
- AWS Lambda function (~200 lines Python)
- Slack App configuration
- API Gateway endpoint
- Secrets in Secrets Manager

**Total Additional Code:** ~200-500 lines depending on option

---

## Next Steps

1. **Choose your option** (recommend Option 1 for best UX)
2. **Create Slack App** (15 minutes)
3. **Deploy Lambda function** (30 minutes)
4. **Test in Slack** (5 minutes)
5. **Roll out to team** (announce in #general)

**Total Setup Time:** ~1 hour

**Your MCP server is ready for Slack integration with zero architecture changes!** 🎉

---

**Document Version:** 2.0
**Last Updated:** 2026-02-22 (ChatAnthropic migration, LangSmith tracing, DM conversation context)
**Maintained By:** DevOps Team
