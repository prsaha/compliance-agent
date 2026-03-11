"""
collection_tools.py — Data collection & sync handlers.

Functions in this module:
  - list_systems_handler            (~line 1027 in mcp_tools.py)
  - start_collection_agent_handler  (~line 1474)
  - stop_collection_agent_handler   (~line 1508)
  - get_collection_agent_status_handler (~line 1539)
  - trigger_manual_sync_handler     (~line 1611)
  - list_all_users_handler          (~line 1648)

Migration status: Re-exporting from mcp_tools (functions not yet moved here).
To complete the split, move each function body here and leave a re-export stub
in mcp_tools.py.
"""

# Re-export from parent module until functions are physically moved here.
from mcp.mcp_tools import (  # noqa: F401
    list_systems_handler,
    start_collection_agent_handler,
    stop_collection_agent_handler,
    get_collection_agent_status_handler,
    trigger_manual_sync_handler,
    list_all_users_handler,
)
