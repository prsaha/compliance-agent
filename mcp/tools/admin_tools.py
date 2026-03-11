"""
admin_tools.py — Session, approval authority, and exception approval routing handlers.

Functions in this module:
  - initialize_session_handler             (~line 4060)
  - check_my_approval_authority_handler    (~line 4180)
  - request_exception_approval_handler     (~line 4284)

Migration status: Re-exporting from mcp_tools (functions not yet moved here).
"""

from mcp.mcp_tools import (  # noqa: F401
    initialize_session_handler,
    check_my_approval_authority_handler,
    request_exception_approval_handler,
)
