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
    SyncMetadata,
    AgentLog,
    Notification,
    AuditTrail,
    UserStatus,
    ViolationSeverity,
    ViolationStatus,
    ScanStatus,
    SyncStatus,
    SyncType
)

from models.approved_exception import (
    ApprovedExceptionModel,
    ExceptionControlModel,
    ExceptionViolationModel,
    ExceptionReviewModel,
    CompensatingControl,
    ExceptionStatus,
    ImplementationStatus,
    RemediationStatus,
    ReviewOutcome,
)

__all__ = [
    # Config
    'Base',
    'DatabaseConfig',
    'get_db_config',
    'get_db_session',
    'init_database',
    'enable_pgvector',
    # Core models
    'User',
    'Role',
    'UserRole',
    'SODRule',
    'Violation',
    'ComplianceScan',
    'SyncMetadata',
    'AgentLog',
    'Notification',
    'AuditTrail',
    # Exception management models
    'ApprovedExceptionModel',
    'ExceptionControlModel',
    'ExceptionViolationModel',
    'ExceptionReviewModel',
    'CompensatingControl',
    # Core enums
    'UserStatus',
    'ViolationSeverity',
    'ViolationStatus',
    'ScanStatus',
    'SyncStatus',
    'SyncType',
    # Exception enums
    'ExceptionStatus',
    'ImplementationStatus',
    'RemediationStatus',
    'ReviewOutcome',
]
