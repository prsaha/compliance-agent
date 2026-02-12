"""
SQLAlchemy ORM Models for SOD Compliance System

Defines all database tables and relationships
"""

from datetime import datetime
from typing import List
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    ForeignKey, Index, Float, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from models.database_config import Base


# Enums
class UserStatus(enum.Enum):
    """User account status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class ViolationSeverity(enum.Enum):
    """Severity levels for SOD violations"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ViolationStatus(enum.Enum):
    """Status of violation"""
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class ScanStatus(enum.Enum):
    """Status of compliance scan"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NotificationChannel(enum.Enum):
    """Notification delivery channels"""
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    DASHBOARD = "DASHBOARD"
    WEBHOOK = "WEBHOOK"


class NotificationStatus(enum.Enum):
    """Status of notification delivery"""
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


# Models
class User(Base):
    """NetSuite users"""
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    internal_id = Column(String(50), unique=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, index=True)
    department = Column(String(255))
    subsidiary = Column(String(255))
    employee_id = Column(String(100))
    last_login = Column(DateTime)

    # NEW: Context fields for SOD analysis
    job_function = Column(String(100), index=True)  # IT/SYSTEMS_ENGINEERING, FINANCE, etc.
    business_unit = Column(String(255))             # Cost center/business unit
    title = Column(String(255))                     # Job title
    supervisor = Column(String(255))                # Manager name
    supervisor_id = Column(String(100))             # Manager internal ID
    location = Column(String(255))                  # Office location
    hire_date = Column(DateTime)                    # Hire date

    synced_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="user", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_user_status_email', 'status', 'email'),
        Index('idx_user_department', 'department'),
        Index('idx_user_job_function', 'job_function'),
    )

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', name='{self.name}', email='{self.email}')>"


class Role(Base):
    """NetSuite roles"""
    __tablename__ = 'roles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(String(100), unique=True, nullable=False, index=True)
    role_name = Column(String(255), nullable=False)
    is_custom = Column(Boolean, default=False)
    description = Column(Text)
    permission_count = Column(Integer, default=0)
    permissions = Column(JSON)  # Store permissions as JSON
    embedding = Column(String)  # pgvector for semantic search (stored as string for now)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role(role_id='{self.role_id}', name='{self.role_name}')>"


class UserRole(Base):
    """Association between users and roles"""
    __tablename__ = 'user_roles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(String(255))
    notes = Column(Text)

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")

    # Indexes
    __table_args__ = (
        Index('idx_user_role_unique', 'user_id', 'role_id', unique=True),
    )

    def __repr__(self):
        return f"<UserRole(user_id='{self.user_id}', role_id='{self.role_id}')>"


class SODRule(Base):
    """Segregation of Duties rules"""
    __tablename__ = 'sod_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)
    category = Column(String(100), index=True)
    description = Column(Text)
    conflicting_permissions = Column(JSON)  # List of conflicting permission patterns
    severity = Column(SQLEnum(ViolationSeverity), default=ViolationSeverity.MEDIUM)
    is_active = Column(Boolean, default=True)
    embedding = Column(String)  # pgvector for semantic search
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    violations = relationship("Violation", back_populates="rule")

    def __repr__(self):
        return f"<SODRule(rule_id='{self.rule_id}', name='{self.rule_name}')>"


class Violation(Base):
    """Detected SOD violations"""
    __tablename__ = 'violations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('sod_rules.id'), nullable=False)
    scan_id = Column(UUID(as_uuid=True), ForeignKey('compliance_scans.id'))

    severity = Column(SQLEnum(ViolationSeverity), nullable=False, index=True)
    status = Column(SQLEnum(ViolationStatus), default=ViolationStatus.OPEN, index=True)
    risk_score = Column(Float, default=0.0)  # 0-100 scale

    title = Column(String(500), nullable=False)
    description = Column(Text)
    conflicting_roles = Column(JSON)  # List of role IDs causing conflict
    conflicting_permissions = Column(JSON)  # Specific permissions in conflict

    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(255))
    resolution_notes = Column(Text)

    embedding = Column(String)  # pgvector for similar violation search
    violation_metadata = Column(JSON)  # Additional context

    # Relationships
    user = relationship("User", back_populates="violations")
    rule = relationship("SODRule", back_populates="violations")
    scan = relationship("ComplianceScan", back_populates="violations")

    # Indexes
    __table_args__ = (
        Index('idx_violation_status_severity', 'status', 'severity'),
        Index('idx_violation_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f"<Violation(user_id='{self.user_id}', severity='{self.severity}', status='{self.status}')>"


class ComplianceScan(Base):
    """Compliance scan execution history"""
    __tablename__ = 'compliance_scans'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_type = Column(String(50), default='AUTOMATED')  # AUTOMATED, MANUAL, SCHEDULED
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.PENDING, index=True)

    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    users_scanned = Column(Integer, default=0)
    violations_found = Column(Integer, default=0)
    violations_critical = Column(Integer, default=0)
    violations_high = Column(Integer, default=0)
    violations_medium = Column(Integer, default=0)
    violations_low = Column(Integer, default=0)

    triggered_by = Column(String(255))
    filters_applied = Column(JSON)
    error_message = Column(Text)
    scan_metadata = Column(JSON)

    # Relationships
    violations = relationship("Violation", back_populates="scan")
    agent_logs = relationship("AgentLog", back_populates="scan")

    def __repr__(self):
        return f"<ComplianceScan(id='{self.id}', status='{self.status}', violations={self.violations_found})>"


class AgentLog(Base):
    """Agent execution logs for monitoring"""
    __tablename__ = 'agent_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey('compliance_scans.id'))
    agent_name = Column(String(100), nullable=False, index=True)
    log_level = Column(String(20), default='INFO')
    message = Column(Text)
    execution_time_ms = Column(Float)
    success = Column(Boolean, default=True)
    error_details = Column(JSON)
    log_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    scan = relationship("ComplianceScan", back_populates="agent_logs")

    # Indexes
    __table_args__ = (
        Index('idx_agent_log_scan_agent', 'scan_id', 'agent_name'),
    )

    def __repr__(self):
        return f"<AgentLog(agent='{self.agent_name}', level='{self.log_level}')>"


class Notification(Base):
    """Notification delivery log"""
    __tablename__ = 'notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    violation_id = Column(UUID(as_uuid=True), ForeignKey('violations.id'))
    notification_type = Column(String(50), nullable=False)  # EMAIL, SLACK, DASHBOARD
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500))
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    delivery_status = Column(String(50), default='PENDING')  # PENDING, SENT, FAILED
    error_message = Column(Text)
    notification_metadata = Column(JSON)

    def __repr__(self):
        return f"<Notification(type='{self.notification_type}', recipient='{self.recipient}')>"


class AuditTrail(Base):
    """Audit trail for compliance actions"""
    __tablename__ = 'audit_trail'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False, index=True)  # USER, ROLE, VIOLATION
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, RESOLVE
    actor = Column(String(255), nullable=False)
    changes = Column(JSON)  # Before/after values
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    audit_metadata = Column(JSON)

    # Indexes
    __table_args__ = (
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<AuditTrail(entity='{self.entity_type}', action='{self.action}', actor='{self.actor}')>"
