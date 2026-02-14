#!/usr/bin/env python3
"""
Local Slack Bot for Compliance Agent MCP Server
Uses Socket Mode for WebSocket-based connection (no webhooks needed)

Setup:
1. pip install slack-bolt anthropic requests python-dotenv
2. Create .env file with tokens
3. Run: python slack_bot_local.py
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
import json
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# MCP Server configuration
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "dev-key-12345")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Available MCP tools (all 14 tools from the compliance agent)
MCP_TOOLS = [
    {
        "name": "initialize_session",
        "description": "Authenticate user and initialize their session with personalized permissions",
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
        "description": "Check what risk levels the current user can approve",
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
        "name": "request_exception_approval",
        "description": "Request approval for a SOD exception with automatic RBAC workflow",
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
                "auto_approve_if_authorized": {"type": "boolean"}
            },
            "required": ["requester_email", "user_identifier", "user_name", "role_names",
                        "conflict_count", "risk_score", "business_justification", "compensating_controls"]
        }
    },
    {
        "name": "record_sod_exception",
        "description": "Record a new SOD exception in the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_identifier": {"type": "string"},
                "user_name": {"type": "string"},
                "role_names": {"type": "array", "items": {"type": "string"}},
                "conflict_count": {"type": "integer"},
                "risk_score": {"type": "number"},
                "business_justification": {"type": "string"},
                "compensating_controls": {"type": "array"},
                "approved_by": {"type": "string"},
                "approval_date": {"type": "string"},
                "review_date": {"type": "string"}
            },
            "required": ["user_identifier", "user_name", "role_names", "conflict_count",
                        "risk_score", "business_justification", "compensating_controls",
                        "approved_by", "approval_date", "review_date"]
        }
    },
    {
        "name": "find_active_exceptions",
        "description": "Find all active SOD exceptions, optionally filtered by user or risk level",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_identifier": {"type": "string"},
                "min_risk_score": {"type": "number"},
                "max_risk_score": {"type": "number"}
            }
        }
    },
    {
        "name": "get_exception_details",
        "description": "Get detailed information about a specific exception by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "exception_id": {"type": "string"}
            },
            "required": ["exception_id"]
        }
    },
    {
        "name": "revoke_exception",
        "description": "Revoke an active SOD exception",
        "input_schema": {
            "type": "object",
            "properties": {
                "exception_id": {"type": "string"},
                "revoked_by": {"type": "string"},
                "revocation_reason": {"type": "string"}
            },
            "required": ["exception_id", "revoked_by", "revocation_reason"]
        }
    },
    {
        "name": "update_compensating_controls",
        "description": "Update compensating controls for an existing exception",
        "input_schema": {
            "type": "object",
            "properties": {
                "exception_id": {"type": "string"},
                "new_controls": {"type": "array"}
            },
            "required": ["exception_id", "new_controls"]
        }
    },
    {
        "name": "extend_exception_review_date",
        "description": "Extend the review date for an active exception",
        "input_schema": {
            "type": "object",
            "properties": {
                "exception_id": {"type": "string"},
                "new_review_date": {"type": "string"},
                "extension_reason": {"type": "string"}
            },
            "required": ["exception_id", "new_review_date", "extension_reason"]
        }
    },
    {
        "name": "detect_new_violations",
        "description": "Scan NetSuite for new SOD violations and compare against approved exceptions",
        "input_schema": {
            "type": "object",
            "properties": {
                "save_results": {"type": "boolean"}
            }
        }
    },
    {
        "name": "get_violations_summary",
        "description": "Get summary statistics of current SOD violations",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_violations_by_risk",
        "description": "Get violations filtered by risk level",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_level": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}
            },
            "required": ["risk_level"]
        }
    },
    {
        "name": "analyze_sod_violation",
        "description": "AI-powered analysis of a specific SOD violation",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_identifier": {"type": "string"},
                "user_name": {"type": "string"},
                "conflicting_roles": {"type": "array", "items": {"type": "string"}},
                "risk_score": {"type": "number"},
                "business_context": {"type": "string"}
            },
            "required": ["user_identifier", "user_name", "conflicting_roles", "risk_score"]
        }
    },
    {
        "name": "query_compliance_knowledge",
        "description": "Query the compliance knowledge base using vector similarity search",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer"}
            },
            "required": ["query"]
        }
    }
]


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Call an MCP tool on the local server using JSON-RPC 2.0 protocol

    Args:
        tool_name: Name of the tool to call
        arguments: Tool arguments

    Returns:
        Tool result as string
    """
    try:
        # Build JSON-RPC 2.0 request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = requests.post(
            f"{MCP_SERVER_URL}/mcp",
            json=mcp_request,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": MCP_API_KEY
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            # Extract result from JSON-RPC response
            if "result" in result:
                content = result["result"].get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", str(result))
                return str(result.get("result"))
            elif "error" in result:
                logger.error(f"MCP tool error: {result['error']}")
                return f"❌ Error calling {tool_name}: {result['error'].get('message', 'Unknown error')}"
            return str(result)
        else:
            logger.error(f"MCP tool call failed: {response.status_code} - {response.text}")
            return f"❌ Error calling {tool_name}: HTTP {response.status_code}"

    except Exception as e:
        logger.error(f"Exception calling MCP tool {tool_name}: {e}")
        return f"❌ Exception calling {tool_name}: {str(e)}"


def process_with_claude(user_message: str, user_email: str) -> str:
    """
    Process user message with Claude and execute any tool calls

    Args:
        user_message: User's message text
        user_email: User's email address

    Returns:
        Claude's response text
    """
    try:
        # Import Anthropic SDK
        from anthropic import Anthropic

        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Build system message with user context
        system_message = f"""You are a Compliance Agent assistant for Segregation of Duties (SOD) management.
The current user is: {user_email}

You have access to 14 MCP tools for:
- Session initialization and RBAC
- SOD exception management
- Violation detection and analysis
- Compliance knowledge queries

When users ask about their permissions, exceptions, violations, or need to perform compliance tasks,
use the appropriate tools to help them.

Always be concise and format responses clearly for Slack."""

        # Call Claude with tools
        response = client.messages.create(
            model="claude-opus-4-6-20250514",
            max_tokens=4096,
            system=system_message,
            messages=[{
                "role": "user",
                "content": user_message
            }],
            tools=MCP_TOOLS
        )

        # Process response and tool calls
        output_text = ""

        for content_block in response.content:
            if content_block.type == "text":
                output_text += content_block.text
            elif content_block.type == "tool_use":
                # Execute tool call
                tool_name = content_block.name
                tool_input = content_block.input

                logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

                # Inject user email if needed
                if "my_email" in str(MCP_TOOLS) and tool_name in ["initialize_session", "check_my_approval_authority"]:
                    if "my_email" not in tool_input:
                        tool_input["my_email"] = user_email

                if "requester_email" in str(MCP_TOOLS) and tool_name == "request_exception_approval":
                    if "requester_email" not in tool_input:
                        tool_input["requester_email"] = user_email

                # Call MCP tool
                tool_result = call_mcp_tool(tool_name, tool_input)
                output_text += f"\n\n{tool_result}"

        return output_text.strip() if output_text else "I processed your request, but have nothing to report."

    except Exception as e:
        logger.error(f"Error processing with Claude: {e}")
        return f"❌ Error processing your request: {str(e)}"


@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle @mention of the bot"""
    try:
        # Get user email
        user_id = event["user"]
        user_info = client.users_info(user=user_id)
        user_email = user_info["user"]["profile"].get("email", "unknown@fivetran.com")

        # Get message text (remove bot mention)
        message_text = event["text"]
        bot_user_id = event.get("bot_user_id") or client.auth_test()["user_id"]
        message_text = message_text.replace(f"<@{bot_user_id}>", "").strip()

        logger.info(f"Processing message from {user_email}: {message_text}")

        # Show typing indicator
        client.chat_postMessage(
            channel=event["channel"],
            thread_ts=event["ts"],
            text="Processing your request..."
        )

        # Process with Claude
        response = process_with_claude(message_text, user_email)

        # Send response
        say(
            text=response,
            thread_ts=event["ts"]
        )

    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            thread_ts=event.get("ts")
        )


@app.event("message")
def handle_dm(event, say, client):
    """Handle direct messages to the bot"""
    # Ignore bot messages and threaded messages
    if event.get("bot_id") or event.get("thread_ts"):
        return

    try:
        # Get user email
        user_id = event["user"]
        user_info = client.users_info(user=user_id)
        user_email = user_info["user"]["profile"].get("email", "unknown@fivetran.com")

        message_text = event["text"]
        logger.info(f"Processing DM from {user_email}: {message_text}")

        # Process with Claude
        response = process_with_claude(message_text, user_email)

        # Send response
        say(text=response)

    except Exception as e:
        logger.error(f"Error handling DM: {e}")
        say(text=f"❌ Sorry, I encountered an error: {str(e)}")


@app.command("/compliance")
def handle_compliance_command(ack, command, say, client):
    """Handle /compliance slash command"""
    ack()

    try:
        # Get user email
        user_id = command["user_id"]
        user_info = client.users_info(user=user_id)
        user_email = user_info["user"]["profile"].get("email", "unknown@fivetran.com")

        command_text = command.get("text", "").strip()

        if not command_text:
            say("""*Compliance Agent Commands:*
• `/compliance who am i` - Initialize session and check your permissions
• `/compliance my authority` - Check your approval authority
• `/compliance violations summary` - Get violations summary
• `/compliance violations critical` - Get critical violations
• `/compliance active exceptions` - List active exceptions
• `/compliance help` - Show this help message

You can also @mention me with natural language requests!""")
            return

        logger.info(f"Processing command from {user_email}: {command_text}")

        # Process with Claude
        response = process_with_claude(command_text, user_email)

        # Send response
        say(text=response)

    except Exception as e:
        logger.error(f"Error handling command: {e}")
        say(text=f"❌ Sorry, I encountered an error: {str(e)}")


def main():
    """Start the Socket Mode handler"""
    # Validate environment variables
    required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please create a .env file with:")
        logger.error("SLACK_BOT_TOKEN=xoxb-your-bot-token")
        logger.error("SLACK_APP_TOKEN=xapp-your-app-token")
        logger.error("ANTHROPIC_API_KEY=sk-ant-your-key")
        logger.error("MCP_SERVER_URL=http://localhost:8080 (optional)")
        sys.exit(1)

    logger.info("Starting Compliance Agent Slack Bot...")
    logger.info(f"MCP Server: {MCP_SERVER_URL}")
    logger.info("Socket Mode: Enabled")
    logger.info("Listening for messages...")

    # Start Socket Mode handler
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()


if __name__ == "__main__":
    main()
