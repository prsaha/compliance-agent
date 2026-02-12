"""Models package - Database ORM models and configuration"""

from models.database_config import (
    Base,
    DatabaseConfig,
    get_db_config,
    get_db_session,
    init_database,
    enable_pgvector
)

from models.database import (
    User,
    Role,
    UserRole,
    SODRule,
    Violation,
    ComplianceScan,
    AgentLog,
    Notification,
    AuditTrail,
    UserStatus,
    ViolationSeverity,
    ViolationStatus,
    ScanStatus
)

__all__ = [
    # Config
    'Base',
    'DatabaseConfig',
    'get_db_config',
    'get_db_session',
    'init_database',
    'enable_pgvector',
    # Models
    'User',
    'Role',
    'UserRole',
    'SODRule',
    'Violation',
    'ComplianceScan',
    'AgentLog',
    'Notification',
    'AuditTrail',
    # Enums
    'UserStatus',
    'ViolationSeverity',
    'ViolationStatus',
    'ScanStatus'
]
