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
import re
import sys
import logging
import threading
import itertools
from typing import Dict, Any, Optional, List
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
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Token / context control
MAX_TOKENS_SLACK = int(os.environ.get("SLACK_MAX_TOKENS", "1024"))
MAX_HISTORY_TURNS = int(os.environ.get("SLACK_MAX_HISTORY_TURNS", "4"))
TOOL_OUTPUT_MAX_CHARS = int(os.environ.get("SLACK_TOOL_OUTPUT_MAX_CHARS", "2000"))

# Global variable to store MCP tools (fetched at startup)
MCP_TOOLS: List[Dict[str, Any]] = []


def fetch_mcp_tools():
    """
    Fetch available tools from the MCP server at startup

    Returns:
        List of tool definitions in Claude API format
    """
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            },
            headers={
                "Content-Type": "application/json",
                "X-API-Key": MCP_API_KEY
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                # Convert MCP tool format to Claude API format
                claude_tools = []
                for tool in tools:
                    claude_tools.append({
                        "name": tool["name"],
                        "description": tool["description"],
                        "input_schema": tool["inputSchema"]
                    })
                logger.info(f"Fetched {len(claude_tools)} tools from MCP server")
                return claude_tools
            else:
                logger.error(f"Unexpected response format: {result}")
                return []
        else:
            logger.error(f"Failed to fetch tools: HTTP {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Error fetching MCP tools: {e}")
        return []


# Old hardcoded tools removed - now fetched dynamically from MCP server


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


def extract_user_mentions(message_text: str, slack_client) -> Dict[str, str]:
    """
    Extract Slack user mentions from message and get their email addresses

    Args:
        message_text: Raw message text with Slack mentions like <@U12345>
        slack_client: Slack client for API calls

    Returns:
        Dict mapping user IDs to email addresses
    """
    import re

    user_map = {}
    # Find all user mentions in format <@U12345>
    user_ids = re.findall(r'<@([A-Z0-9]+)>', message_text)

    for user_id in user_ids:
        try:
            user_info = slack_client.users_info(user=user_id)
            email = user_info["user"]["profile"].get("email")
            name = user_info["user"]["real_name"]
            if email:
                user_map[user_id] = {
                    "email": email,
                    "name": name
                }
                logger.info(f"Resolved @{name} to {email}")
        except Exception as e:
            logger.warning(f"Could not resolve user {user_id}: {e}")

    return user_map


def _sanitize_tool_output(tool_name: str, raw_output: str) -> str:
    """
    Trim tool output to TOOL_OUTPUT_MAX_CHARS characters before feeding back to Claude.
    Large tool outputs (e.g., list_all_users) would otherwise blow up the context.
    """
    if len(raw_output) <= TOOL_OUTPUT_MAX_CHARS:
        return raw_output
    trimmed = raw_output[:TOOL_OUTPUT_MAX_CHARS]
    logger.info(f"Tool output for '{tool_name}' trimmed from {len(raw_output)} to {TOOL_OUTPUT_MAX_CHARS} chars")
    return trimmed + f"\n\n[Output truncated — {len(raw_output) - TOOL_OUTPUT_MAX_CHARS} chars omitted]"


def _trim_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keep at most MAX_HISTORY_TURNS turn-pairs (user + assistant) to cap context growth.
    Always preserves the first user message (turn 0).
    """
    if len(messages) <= MAX_HISTORY_TURNS * 2:
        return messages
    # Keep the last MAX_HISTORY_TURNS * 2 messages
    return messages[-(MAX_HISTORY_TURNS * 2):]


_THINKING_STAGES = itertools.cycle([
    "⏳ _Analyzing your request..._",
    "🔍 _Querying compliance data..._",
    "🧠 _Reasoning about SOD rules..._",
    "📊 _Processing results..._",
    "✍️ _Drafting response..._",
])


def _animate_thinking(client, channel: str, thinking_ts: str, stop_event: threading.Event):
    """Cycle through thinking stage labels every 2.5 s until stop_event is set."""
    for stage in _THINKING_STAGES:
        if stop_event.wait(timeout=2.5):
            break
        try:
            client.chat_update(channel=channel, ts=thinking_ts, text=stage)
        except Exception:
            break


def format_as_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Convert Claude's mrkdwn response into Slack Block Kit blocks.
    Splits on '---' dividers and respects Slack's 3000-char block limit.
    """
    blocks = []
    sections = re.split(r'\n---+\n', text.strip())

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        # Slack section block text limit is 3000 chars
        if len(section) > 3000:
            section = section[:2997] + "…"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": section}
        })

        if i < len(sections) - 1:
            blocks.append({"type": "divider"})

    return blocks or [{"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}}]


def process_with_claude(user_message: str, user_email: str, mentioned_users: Optional[Dict[str, Dict]] = None) -> str:
    """
    Process user message with Claude and execute any tool calls

    Args:
        user_message: User's message text
        user_email: User's email address

    Returns:
        Claude's response text
    """
    try:
        # Use tracking wrapper so all Slack bot calls appear in cost reports
        from utils.anthropic_wrapper import AnthropicClientWrapper
        from utils.tool_router import select_tools_for_intent

        client = AnthropicClientWrapper(agent_name="slack_bot", api_key=ANTHROPIC_API_KEY)

        # ── Static system content (cache-eligible — identical across all users/turns) ──
        _STATIC_SYSTEM = (
            "You are a Compliance Agent for Segregation of Duties (SOD) and user access review. "
            "For access requests: (1) get current roles, (2) check job appropriateness, "
            "(3) call analyze_access_request with ALL roles combined — never analyze a single role in isolation. "
            "Flag Finance roles for non-Finance users and vice versa. "
            "Be concise.\n\n"
            "FORMATTING — you are responding inside Slack. Use Slack mrkdwn, NOT standard Markdown:\n"
            "• Bold: *text* (single asterisk, not double)\n"
            "• Italic: _text_\n"
            "• Inline code: `code`\n"
            "• Code block: ```code```\n"
            "• Bullet list: start lines with • or -\n"
            "• Section separator: a line containing only --- (three dashes)\n"
            "• DO NOT use ### or ## headings — use *Bold Title* on its own line instead\n"
            "• DO NOT use Markdown tables (| col | col |) — use bullet lists or numbered lists\n"
            "• DO NOT use **double asterisks** — Slack ignores them\n"
            "• Emojis are fine and encouraged for visual hierarchy"
        )

        # ── Dynamic context appended per-call (not cached — contains user-specific data) ──
        dynamic_parts = [f"Current user: {user_email}"]
        if mentioned_users:
            dynamic_parts.append("Mentioned users:")
            for _uid, info in mentioned_users.items():
                dynamic_parts.append(f"  @{info['name']}: {info['email']}")
            dynamic_parts.append(
                "Use these emails with get_user_violations / analyze_access_request automatically."
            )
        dynamic_context = "\n".join(dynamic_parts)

        # System passed as a list to enable cache_control on the static portion
        system = [
            {
                "type": "text",
                "text": _STATIC_SYSTEM,
                "cache_control": {"type": "ephemeral"}   # Prefix cache — re-read at 10% cost
            },
            {
                "type": "text",
                "text": dynamic_context
            }
        ]

        # Select only the tools relevant to this message (saves ~8K tokens per request)
        relevant_tools = select_tools_for_intent(user_message, MCP_TOOLS) if MCP_TOOLS else []

        # Multi-turn agentic tool use loop
        messages = [{
            "role": "user",
            "content": user_message
        }]

        final_text = ""
        max_turns = 5  # Prevent infinite loops

        for turn in range(max_turns):
            # Trim history to avoid unbounded context growth
            trimmed_messages = _trim_history(messages)

            # Call Claude with token-efficient settings
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=MAX_TOKENS_SLACK,
                system=system,
                messages=trimmed_messages,
                tools=relevant_tools if relevant_tools else MCP_TOOLS,
                operation=f"slack_turn_{turn + 1}"
            )

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Extract final text
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text
                break

            # Process tool calls
            tool_uses = []
            tool_results = []

            for content_block in response.content:
                if content_block.type == "text":
                    final_text += content_block.text
                elif content_block.type == "tool_use":
                    tool_uses.append(content_block)

                    # Execute tool call
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_use_id = content_block.id

                    logger.info(f"Turn {turn+1}: Executing tool: {tool_name} with input: {tool_input}")

                    # Inject user email if needed
                    if "my_email" in str(MCP_TOOLS) and tool_name in ["initialize_session", "check_my_approval_authority"]:
                        if "my_email" not in tool_input:
                            tool_input["my_email"] = user_email

                    if "requester_email" in str(MCP_TOOLS) and tool_name == "request_exception_approval":
                        if "requester_email" not in tool_input:
                            tool_input["requester_email"] = user_email

                    # Call MCP tool and sanitize output to control token growth
                    raw_tool_result = call_mcp_tool(tool_name, tool_input)
                    tool_result = _sanitize_tool_output(tool_name, raw_tool_result)

                    # Add to results
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": tool_result
                    })

            # If no tool calls, we're done
            if not tool_uses:
                break

            # Continue conversation with tool results
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            messages.append({
                "role": "user",
                "content": tool_results
            })

        return final_text.strip() if final_text else "I processed your request, but have nothing to report."

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
        message_text_clean = message_text.replace(f"<@{bot_user_id}>", "").strip()

        # Extract mentioned users
        mentioned_users = extract_user_mentions(message_text, client)

        logger.info(f"Processing message from {user_email}: {message_text_clean}")
        if mentioned_users:
            logger.info(f"Mentioned users: {list(mentioned_users.values())}")

        # Post initial thinking message and animate it while Claude processes
        channel = event["channel"]
        thinking_result = client.chat_postMessage(
            channel=channel,
            thread_ts=event["ts"],
            text="⏳ _Analyzing your request..._"
        )
        thinking_ts = thinking_result["ts"]

        stop_event = threading.Event()
        anim_thread = threading.Thread(
            target=_animate_thinking,
            args=(client, channel, thinking_ts, stop_event),
            daemon=True
        )
        anim_thread.start()

        try:
            response = process_with_claude(message_text_clean, user_email, mentioned_users)
        finally:
            stop_event.set()
            anim_thread.join(timeout=3)

        # Update the thinking message in-place with the real response
        client.chat_update(
            channel=channel,
            ts=thinking_ts,
            text=response,
            blocks=format_as_blocks(response)
        )

    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ Sorry, I encountered an error: {str(e)}"}}],
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

        # Extract mentioned users
        mentioned_users = extract_user_mentions(message_text, client)

        logger.info(f"Processing DM from {user_email}: {message_text}")
        if mentioned_users:
            logger.info(f"Mentioned users: {list(mentioned_users.values())}")

        # Post initial thinking message and animate it while Claude processes
        channel = event["channel"]
        thinking_result = client.chat_postMessage(
            channel=channel,
            text="⏳ _Analyzing your request..._"
        )
        thinking_ts = thinking_result["ts"]

        stop_event = threading.Event()
        anim_thread = threading.Thread(
            target=_animate_thinking,
            args=(client, channel, thinking_ts, stop_event),
            daemon=True
        )
        anim_thread.start()

        try:
            response = process_with_claude(message_text, user_email, mentioned_users)
        finally:
            stop_event.set()
            anim_thread.join(timeout=3)

        # Update the thinking message in-place with the real response
        client.chat_update(
            channel=channel,
            ts=thinking_ts,
            text=response,
            blocks=format_as_blocks(response)
        )

    except Exception as e:
        logger.error(f"Error handling DM: {e}")
        say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ Sorry, I encountered an error: {str(e)}"}}]
        )


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
            help_text = (
                "*Compliance Agent Commands:*\n"
                "• `/compliance who am i` — Initialize session and check your permissions\n"
                "• `/compliance my authority` — Check your approval authority\n"
                "• `/compliance violations summary` — Get violations summary\n"
                "• `/compliance violations critical` — Get critical violations\n"
                "• `/compliance active exceptions` — List active exceptions\n"
                "• `/compliance help` — Show this help message\n\n"
                "You can also @mention me with natural language requests!"
            )
            say(text=help_text, blocks=format_as_blocks(help_text))
            return

        # Extract mentioned users
        mentioned_users = extract_user_mentions(command_text, client)

        logger.info(f"Processing command from {user_email}: {command_text}")
        if mentioned_users:
            logger.info(f"Mentioned users: {list(mentioned_users.values())}")

        # Process with Claude
        response = process_with_claude(command_text, user_email, mentioned_users)

        # Send response using Block Kit for proper Slack rendering
        say(text=response, blocks=format_as_blocks(response))

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

    # Fetch available tools from MCP server
    global MCP_TOOLS
    MCP_TOOLS = fetch_mcp_tools()

    if not MCP_TOOLS:
        logger.error("Failed to fetch tools from MCP server. Bot may not function correctly.")
        logger.error("Please ensure the MCP server is running at: " + MCP_SERVER_URL)
        sys.exit(1)

    logger.info("Socket Mode: Enabled")
    logger.info("Listening for messages...")

    # Start Socket Mode handler
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()


if __name__ == "__main__":
    main()
