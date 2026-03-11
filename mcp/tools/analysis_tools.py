"""
analysis_tools.py — SOD analysis, access review, role conflict, knowledge-base handlers.

Functions in this module:
  - perform_access_review_handler          (~line 1067)
  - analyze_access_request_handler         (~line 1711)
  - query_sod_rules_handler                (~line 1880)
  - get_compensating_controls_handler      (~line 1953)
  - validate_job_role_handler              (~line 2033)
  - check_permission_conflict_handler      (~line 2122)
  - get_permission_categories_handler      (~line 2182)
  - search_permissions_handler             (~line 2233)
  - query_knowledge_base_handler           (~line 2308)
  - recommend_roles_for_job_title_handler  (~line 2404)
  - analyze_role_permissions_handler       (~line 2478)
  - get_role_conflicts_handler             (~line 2770)
  - get_role_risk_matrix_handler           (~line 4830)

Migration status: Re-exporting from mcp_tools (functions not yet moved here).
"""

from mcp.mcp_tools import (  # noqa: F401
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
