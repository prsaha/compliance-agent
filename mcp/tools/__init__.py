"""
mcp/tools — Phase-based handler modules for compliance MCP tools.

Each sub-module owns one phase of the compliance workflow:

    collection_tools.py   — Data collection & sync (start/stop/status/trigger, list_all_users, list_systems)
    analysis_tools.py     — SOD analysis & access review (analyze_access_request, role conflicts, knowledge base)
    violation_tools.py    — Violation queries & remediation (get_user_violations, stats, report, remediate)
    exception_tools.py    — Exception lifecycle (record, find_similar, review, effectiveness)
    admin_tools.py        — Session init, approval authority, exception approval routing

All handlers are currently re-exported from the parent mcp_tools module for
backwards compatibility while the split is in progress.

Completed handlers should be moved here one-by-one, with a re-export stub
left in mcp_tools.py for zero-downtime migration:

    # mcp_tools.py
    from mcp.tools.collection_tools import start_collection_agent_handler  # moved
"""

from mcp.tools.collection_tools import (
    list_systems_handler,
    start_collection_agent_handler,
    stop_collection_agent_handler,
    get_collection_agent_status_handler,
    trigger_manual_sync_handler,
    list_all_users_handler,
)

from mcp.tools.analysis_tools import (
    perform_access_review_handler,
    analyze_access_request_handler,
    query_sod_rules_handler,
    get_compensating_controls_handler,
    validate_job_role_handler,
    check_permission_conflict_handler,
    get_permission_categories_handler,
    search_permissions_handler,
    query_knowledge_base_handler,
    recommend_roles_for_job_title_handler,
    analyze_role_permissions_handler,
    get_role_conflicts_handler,
    get_role_risk_matrix_handler,
)

from mcp.tools.violation_tools import (
    get_user_violations_handler,
    remediate_violation_handler,
    schedule_review_handler,
    get_violation_stats_handler,
    list_violations_handler,
    generate_violation_report_handler,
)

from mcp.tools.exception_tools import (
    record_exception_approval_handler,
    find_similar_exceptions_handler,
    get_exception_details_handler,
    list_approved_exceptions_handler,
    record_exception_violation_handler,
    get_exception_effectiveness_stats_handler,
    detect_exception_violations_handler,
    conduct_exception_review_handler,
    get_exceptions_for_review_handler,
)

from mcp.tools.admin_tools import (
    initialize_session_handler,
    check_my_approval_authority_handler,
    request_exception_approval_handler,
)

__all__ = [
    # collection
    "list_systems_handler",
    "start_collection_agent_handler",
    "stop_collection_agent_handler",
    "get_collection_agent_status_handler",
    "trigger_manual_sync_handler",
    "list_all_users_handler",
    # analysis
    "perform_access_review_handler",
    "analyze_access_request_handler",
    "query_sod_rules_handler",
    "get_compensating_controls_handler",
    "validate_job_role_handler",
    "check_permission_conflict_handler",
    "get_permission_categories_handler",
    "search_permissions_handler",
    "query_knowledge_base_handler",
    "recommend_roles_for_job_title_handler",
    "analyze_role_permissions_handler",
    "get_role_conflicts_handler",
    "get_role_risk_matrix_handler",
    # violations
    "get_user_violations_handler",
    "remediate_violation_handler",
    "schedule_review_handler",
    "get_violation_stats_handler",
    "list_violations_handler",
    "generate_violation_report_handler",
    # exceptions
    "record_exception_approval_handler",
    "find_similar_exceptions_handler",
    "get_exception_details_handler",
    "list_approved_exceptions_handler",
    "record_exception_violation_handler",
    "get_exception_effectiveness_stats_handler",
    "detect_exception_violations_handler",
    "conduct_exception_review_handler",
    "get_exceptions_for_review_handler",
    # admin
    "initialize_session_handler",
    "check_my_approval_authority_handler",
    "request_exception_approval_handler",
]
