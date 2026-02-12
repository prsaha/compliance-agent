"""
MCP Tools - Tool definitions and handlers for Claude UI integration

Each tool represents a capability that Claude can invoke via MCP protocol.
"""
from typing import List, Dict, Any, Optional
import logging
from .orchestrator import ComplianceOrchestrator

logger = logging.getLogger(__name__)

# Initialize orchestrator (singleton)
_orchestrator = None


def get_orchestrator() -> ComplianceOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ComplianceOrchestrator()
    return _orchestrator


# ============================================================================
# TOOL SCHEMAS
# ============================================================================

TOOL_SCHEMAS = {
    "list_systems": {
        "description": "List all available systems for compliance review with their current status and user counts",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    "perform_access_review": {
        "description": "Perform a comprehensive user access review for a specific system, analyzing SOD violations and generating recommendations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "Name of the system to review",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis to perform",
                    "enum": ["sod_violations", "excessive_permissions", "inactive_users", "all"],
                    "default": "sod_violations"
                },
                "include_recommendations": {
                    "type": "boolean",
                    "description": "Include AI-powered remediation recommendations",
                    "default": True
                }
            },
            "required": ["system_name"]
        }
    },

    "get_user_violations": {
        "description": "Get detailed violation information for a specific user, including AI-powered risk analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System name where user exists",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "user_identifier": {
                    "type": "string",
                    "description": "User email address or user ID"
                },
                "include_ai_analysis": {
                    "type": "boolean",
                    "description": "Include AI-powered risk analysis and recommendations",
                    "default": True
                }
            },
            "required": ["system_name", "user_identifier"]
        }
    },

    "remediate_violation": {
        "description": "Create a remediation plan or ticket for a specific violation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "violation_id": {
                    "type": "string",
                    "description": "UUID of the violation to remediate"
                },
                "action": {
                    "type": "string",
                    "description": "Type of remediation action to take",
                    "enum": ["remove_role", "request_approval", "create_ticket", "notify_manager"]
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes or context for remediation"
                }
            },
            "required": ["violation_id", "action"]
        }
    },

    "schedule_review": {
        "description": "Schedule a recurring compliance review for a system",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System to review",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "frequency": {
                    "type": "string",
                    "description": "Review frequency",
                    "enum": ["daily", "weekly", "monthly"]
                },
                "day_of_week": {
                    "type": "string",
                    "description": "Day of week for weekly reviews",
                    "enum": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                },
                "time": {
                    "type": "string",
                    "description": "Time in HH:MM format (24-hour)",
                    "pattern": "^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone identifier",
                    "default": "America/Los_Angeles"
                }
            },
            "required": ["system_name", "frequency"]
        }
    },

    "get_violation_stats": {
        "description": "Get aggregate violation statistics across systems for a time period",
        "inputSchema": {
            "type": "object",
            "properties": {
                "systems": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of systems to include (empty array = all systems)"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for statistics",
                    "enum": ["today", "week", "month", "quarter", "year"],
                    "default": "month"
                }
            },
            "required": []
        }
    }
}


# ============================================================================
# TOOL HANDLERS
# ============================================================================

async def list_systems_handler() -> str:
    """
    List all available systems

    Returns:
        Formatted string with system information
    """
    try:
        orchestrator = get_orchestrator()
        systems = await orchestrator.list_available_systems()

        if not systems:
            return "No systems configured. Please configure system connectors."

        result = "**Available Systems for Compliance Review:**\n\n"

        for system in systems:
            status_emoji = "✅" if system['status'] == "connected" else "❌"
            result += f"{status_emoji} **{system['name'].upper()}** ({system['type']})\n"
            result += f"   • Status: {system['status']}\n"
            result += f"   • Users: {system['user_count']:,}\n"
            result += f"   • Last reviewed: {system['last_review']}\n\n"

        return result

    except Exception as e:
        logger.error(f"Error in list_systems_handler: {str(e)}", exc_info=True)
        return f"Error listing systems: {str(e)}"


async def perform_access_review_handler(
    system_name: str,
    analysis_type: str = "sod_violations",
    include_recommendations: bool = True
) -> str:
    """
    Perform access review

    Returns:
        Formatted string with review results
    """
    try:
        logger.info(f"Performing access review: {system_name}")

        orchestrator = get_orchestrator()
        result = await orchestrator.perform_access_review(
            system_name=system_name,
            analysis_type=analysis_type,
            include_recommendations=include_recommendations
        )

        # Format response
        output = f"**Access Review Complete - {result['system_name'].upper()}**\n\n"
        output += f"📊 **Summary:**\n"
        output += f"   • Users Analyzed: {result['users_analyzed']:,}\n"
        output += f"   • Total Violations: {result['total_violations']:,}\n"
        output += f"   • High-Risk: {result['high_risk_count']} 🔴\n"
        output += f"   • Medium-Risk: {result['medium_risk_count']} 🟡\n"
        output += f"   • Low-Risk: {result['low_risk_count']} 🟢\n"
        output += f"   • Execution Time: {result['execution_time_seconds']}s\n\n"

        if result['top_violators']:
            output += "👥 **Top Violators:**\n"
            for i, user in enumerate(result['top_violators'][:5], 1):
                output += f"{i}. **{user['name']}** ({user['email']})\n"
                output += f"   └─ {user['violation_count']} violations "
                output += f"({user['high_risk']} high, {user['medium_risk']} medium, {user['low_risk']} low)\n"
            output += "\n"

        if include_recommendations and result.get('recommendations'):
            output += f"💡 **Recommendations:**\n{result['recommendations']}\n\n"

        output += "ℹ️  _Use `get_user_violations` to see details for specific users._"

        return output

    except Exception as e:
        logger.error(f"Error in perform_access_review_handler: {str(e)}", exc_info=True)
        return f"❌ Error performing access review: {str(e)}"


async def get_user_violations_handler(
    system_name: str,
    user_identifier: str,
    include_ai_analysis: bool = True
) -> str:
    """
    Get user violation details

    Returns:
        Formatted string with user violations
    """
    try:
        logger.info(f"Fetching violations for user: {user_identifier}")

        orchestrator = get_orchestrator()
        result = await orchestrator.get_user_violations(
            system_name=system_name,
            user_identifier=user_identifier,
            include_ai_analysis=include_ai_analysis
        )

        # Format response
        output = f"**{result['user_name']} - Violation Report**\n\n"
        output += f"📧 Email: {result['email']}\n"
        output += f"🏢 System: {result['system']}\n"
        output += f"🎭 Roles ({result['role_count']}): {', '.join(result['roles'])}\n"
        output += f"⚠️  Total Violations: {result['violation_count']}\n"
        if result.get('department'):
            output += f"📁 Department: {result['department']}\n"
        output += f"✅ Status: {'Active' if result['is_active'] else 'Inactive'}\n\n"

        if result['violations']:
            output += "**Violations:**\n\n"
            for i, v in enumerate(result['violations'], 1):
                severity_emoji = "🔴" if v['severity'] == "HIGH" else "🟡" if v['severity'] == "MEDIUM" else "🟢"
                output += f"{i}. {severity_emoji} **{v['severity']}**: {v['rule_name']}\n"
                output += f"   • Description: {v['description']}\n"
                output += f"   • Risk: {v['risk_description']}\n"
                output += f"   • Status: {v['status']}\n"
                output += f"   • Detected: {v['detected_at']}\n"
                output += f"   • Violation ID: `{v['id']}`\n\n"

        if include_ai_analysis and result.get('ai_analysis'):
            output += f"🤖 **AI Risk Analysis:**\n{result['ai_analysis']}\n\n"

        output += "ℹ️  _Use `remediate_violation` with a violation ID to create a remediation plan._"

        return output

    except Exception as e:
        logger.error(f"Error in get_user_violations_handler: {str(e)}", exc_info=True)
        return f"❌ Error fetching user violations: {str(e)}"


async def remediate_violation_handler(
    violation_id: str,
    action: str,
    notes: str = ""
) -> str:
    """
    Create remediation plan

    Returns:
        Formatted string with remediation status
    """
    try:
        logger.info(f"Creating remediation: {violation_id}, {action}")

        orchestrator = get_orchestrator()
        result = await orchestrator.remediate_violation(
            violation_id=violation_id,
            action=action,
            notes=notes
        )

        # Format response
        output = "✅ **Remediation Initiated**\n\n"
        output += f"📋 Ticket ID: `{result['ticket_id']}`\n"
        output += f"👤 User: {result['user_name']} ({result['user_email']})\n"
        output += f"⚠️  Violation ID: `{result['violation_id']}`\n"
        output += f"🔧 Action: {result['action']}\n"
        output += f"📝 Status: {result['status']}\n"

        if notes:
            output += f"💬 Notes: {notes}\n"

        if result.get('next_steps'):
            output += f"\n📌 **Next Steps:**\n"
            for step in result['next_steps']:
                output += f"   • {step}\n"

        output += f"\n⏰ Created: {result['created_at']}"

        return output

    except Exception as e:
        logger.error(f"Error in remediate_violation_handler: {str(e)}", exc_info=True)
        return f"❌ Error creating remediation: {str(e)}"


async def schedule_review_handler(
    system_name: str,
    frequency: str,
    day_of_week: Optional[str] = None,
    time: Optional[str] = None,
    timezone: str = "America/Los_Angeles"
) -> str:
    """
    Schedule recurring review

    Returns:
        Formatted string with schedule confirmation
    """
    try:
        logger.info(f"Scheduling review: {system_name}, {frequency}")

        orchestrator = get_orchestrator()
        result = await orchestrator.schedule_review(
            system_name=system_name,
            frequency=frequency,
            day_of_week=day_of_week,
            time=time,
            timezone=timezone
        )

        # Format response
        output = "✅ **Review Scheduled Successfully**\n\n"
        output += f"🏢 System: {result['system_name']}\n"
        output += f"🔄 Frequency: {result['frequency']}\n"
        output += f"📅 Schedule: {result['schedule_description']}\n"
        output += f"⏰ Next Run: {result['next_run']}\n"
        output += f"🌍 Timezone: {result['timezone']}\n\n"

        output += "📬 **Notifications will be sent via:**\n"
        for channel in result['notification_channels']:
            output += f"   • {channel}\n"

        output += "\nℹ️  _You'll receive a notification when each review completes._"

        return output

    except Exception as e:
        logger.error(f"Error in schedule_review_handler: {str(e)}", exc_info=True)
        return f"❌ Error scheduling review: {str(e)}"


async def get_violation_stats_handler(
    systems: List[str] = None,
    time_range: str = "month"
) -> str:
    """
    Get violation statistics

    Returns:
        Formatted string with statistics
    """
    try:
        logger.info(f"Fetching violation stats: {time_range}")

        orchestrator = get_orchestrator()
        result = await orchestrator.get_violation_stats(
            systems=systems if systems else None,
            time_range=time_range
        )

        # Format response
        output = f"**Violation Statistics - {time_range.capitalize()}**\n\n"
        output += f"📊 **Overview:**\n"
        output += f"   • Systems Analyzed: {result['system_count']}\n"
        output += f"   • Total Users: {result['total_users']:,}\n"
        output += f"   • Total Violations: {result['total_violations']:,}\n\n"

        output += f"🎯 **Risk Distribution:**\n"
        output += f"   • 🔴 High-Risk: {result['high_risk']} ({result['high_risk_percent']}%)\n"
        output += f"   • 🟡 Medium-Risk: {result['medium_risk']} ({result['medium_risk_percent']}%)\n"
        output += f"   • 🟢 Low-Risk: {result['low_risk']} ({result['low_risk_percent']}%)\n\n"

        if result['by_system']:
            output += f"🏢 **Violations by System:**\n"
            for system in result['by_system']:
                output += f"   • {system['name']}: {system['violation_count']} violations\n"

        output += f"\n📈 **Trend:** {result['trend_description']}"

        return output

    except Exception as e:
        logger.error(f"Error in get_violation_stats_handler: {str(e)}", exc_info=True)
        return f"❌ Error fetching statistics: {str(e)}"


# ============================================================================
# TOOL REGISTRY
# ============================================================================

TOOL_HANDLERS = {
    "list_systems": list_systems_handler,
    "perform_access_review": perform_access_review_handler,
    "get_user_violations": get_user_violations_handler,
    "remediate_violation": remediate_violation_handler,
    "schedule_review": schedule_review_handler,
    "get_violation_stats": get_violation_stats_handler
}


def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """Get schema for a specific tool"""
    return TOOL_SCHEMAS.get(tool_name)


def get_all_tool_schemas() -> Dict[str, Any]:
    """Get all tool schemas"""
    return TOOL_SCHEMAS


def get_tool_handler(tool_name: str):
    """Get handler function for a tool"""
    return TOOL_HANDLERS.get(tool_name)
