"""
Tool Router — Intent-based MCP tool selection for the Slack bot.

Reduces token usage by sending only the 3-5 tools relevant to the user's intent
instead of the full 35-tool schema on every request (~10K tokens → ~1.5K tokens).

Usage:
    from utils.tool_router import select_tools_for_intent

    relevant_tools = select_tools_for_intent(user_message, all_tools)
    # Pass relevant_tools to Claude instead of all_tools
"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool groups — map intent keywords to tool name sets
# ---------------------------------------------------------------------------

TOOL_GROUPS: Dict[str, List[str]] = {
    "access_review": [
        "get_user_violations",
        "analyze_access_request",
        "validate_job_role",
        "get_role_conflicts",
        "recommend_roles_for_job_title",
    ],
    "violation_query": [
        "get_violation_stats",
        "list_violations",
        "get_violation_details",
        "get_user_violations",
        "get_violation_history",
    ],
    "exception_mgmt": [
        "request_exception_approval",
        "check_my_approval_authority",
        "get_exception_details",
        "list_active_exceptions",
        "approve_exception",
        "revoke_exception",
    ],
    "sod_rules": [
        "query_sod_rules",
        "get_sod_rule_details",
        "list_sod_rules",
    ],
    "knowledge": [
        "query_knowledge_base",
        "get_compensating_controls",
        "get_permission_categories",
        "search_permissions",
    ],
    "role_analysis": [
        "analyze_role_permissions",
        "get_role_conflicts",
        "recommend_roles_for_job_title",
        "validate_job_role",
    ],
    "role_risk": [
        "get_role_risk_matrix",
        "get_role_conflicts",
        "list_violations",
    ],
    "reporting": [
        "get_violation_stats",
        "generate_compliance_report",
        "get_org_risk_assessment",
        "export_report",
    ],
    "system": [
        "list_systems",
        "get_system_status",
        "trigger_manual_sync",
        "get_sync_status",
        "initialize_session",
    ],
    "remediation": [
        "remediate_violation",
        "schedule_review",
        "create_remediation_ticket",
        "notify_manager",
    ],
}

# ---------------------------------------------------------------------------
# Intent classifiers — simple keyword/regex matching
# ---------------------------------------------------------------------------

INTENT_PATTERNS: Dict[str, List[str]] = {
    "access_review": [
        r"\bcan\b.*\bassign\b",
        r"\bshould\b.*\bget\b.*\brole\b",
        r"\baccess request\b",
        r"\brole request\b",
        r"\bpermission request\b",
        r"\bcheck.*access\b",
        r"\banalyze.*access\b",
        r"\brevoke.*access\b",
    ],
    "violation_query": [
        r"\bviolation\b",
        r"\bviolations\b",
        r"\bsod conflict\b",
        r"\bconflicts?\b",
        r"\bcompliance issue\b",
    ],
    "exception_mgmt": [
        r"\bexception\b",
        r"\bapproval\b",
        r"\bapprove\b",
        r"\bwaiver\b",
        r"\bexemption\b",
    ],
    "sod_rules": [
        r"\bsod rule\b",
        r"\bsegregation of duties\b",
        r"\brule\b.*\bcheck\b",
        r"\bwhat rules\b",
        r"\blist.*rules\b",
    ],
    "knowledge": [
        r"\bcompensating control\b",
        r"\bbest practice\b",
        r"\bpolicy\b",
        r"\bguidance\b",
        r"\bknowledge base\b",
        r"\bhow to remediate\b",
    ],
    "role_analysis": [
        r"\brole.*permission\b",
        r"\bpermission.*role\b",
        r"\banalyze.*role\b",
        r"\brole conflict\b",
        r"\binside.*role\b",
    ],
    "role_risk": [
        r"\ball.*roles?\b",
        r"\bcustom roles?\b",
        r"\bfivetran roles?\b",
        r"\broles?.*isolation\b",
        r"\broles?.*combination\b",
        r"\brisky roles?\b",
        r"\brole.*risk\b",
        r"\brole.*matrix\b",
        r"\bwhich roles?\b",
        r"\boveral.*observation\b",
        r"\bobservation.*roles?\b",
    ],
    "reporting": [
        r"\breport\b",
        r"\bsummary\b",
        r"\bstatistic\b",
        r"\boverview\b",
        r"\bdashboard\b",
        r"\brisk.*assessment\b",
        r"\borg.*risk\b",
    ],
    "remediation": [
        r"\bremediat\b",
        r"\bfix\b.*\bviolation\b",
        r"\bschedule.*review\b",
        r"\bticket\b",
        r"\bnotif.*manager\b",
    ],
    "system": [
        r"\bsync\b",
        r"\bsystem status\b",
        r"\bsystems\b",
        r"\bhealth\b",
        r"\bstatus\b",
    ],
}


def classify_intent(user_message: str) -> List[str]:
    """
    Classify the user message into one or more intent groups.

    Args:
        user_message: Raw Slack message text

    Returns:
        List of matched intent group names (e.g., ['access_review', 'violation_query'])
    """
    text = user_message.lower()
    matched = []

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                matched.append(intent)
                break

    # Default to most common intents if nothing matched
    if not matched:
        matched = ["access_review", "violation_query"]
        logger.debug(f"No intent matched for message — defaulting to {matched}")
    else:
        logger.debug(f"Detected intents: {matched}")

    return matched


def select_tools_for_intent(
    user_message: str,
    all_tools: List[Dict[str, Any]],
    always_include: Optional[List[str]] = None,
    max_tools: int = 8
) -> List[Dict[str, Any]]:
    """
    Return the subset of MCP tools relevant to the user's intent.

    Always includes 'initialize_session' to maintain user context, plus
    tools from the matched intent groups (up to max_tools).

    Args:
        user_message: Raw user message
        all_tools: Full list of MCP tool schemas
        always_include: Tool names to always include regardless of intent
        max_tools: Maximum number of tools to return

    Returns:
        Filtered list of tool schema dicts
    """
    always_include = always_include or ["initialize_session", "check_my_approval_authority"]

    # Build name → schema index
    tool_index = {t["name"]: t for t in all_tools if "name" in t}

    intents = classify_intent(user_message)

    # Collect relevant tool names in order
    selected_names: List[str] = list(always_include)
    for intent in intents:
        for name in TOOL_GROUPS.get(intent, []):
            if name not in selected_names:
                selected_names.append(name)
            if len(selected_names) >= max_tools:
                break
        if len(selected_names) >= max_tools:
            break

    # Map names back to schemas, skipping any that don't exist in the full set
    result = [tool_index[name] for name in selected_names if name in tool_index]

    # If we ended up with too few tools (e.g., many missing), pad with top tools
    if len(result) < 3 and all_tools:
        result = all_tools[:max_tools]

    logger.info(
        f"Tool routing: {len(all_tools)} total → {len(result)} selected "
        f"(intents: {intents})"
    )
    return result
