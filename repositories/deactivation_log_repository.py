"""
Deactivation Log Repository

Data access layer for user deactivation audit logs
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from models.database import DeactivationLog, DeactivationAction, ExecutionMethod
import logging

logger = logging.getLogger(__name__)


class DeactivationLogRepository:
    """Repository for deactivation log operations"""

    def __init__(self, session: Session):
        self.session = session

    def create_log(self, log_data: Dict[str, Any]) -> DeactivationLog:
        """Create a new deactivation log entry"""
        log = DeactivationLog(
            netsuite_user_id=log_data.get('netsuite_user_id'),
            netsuite_internal_id=log_data.get('netsuite_internal_id'),
            email=log_data['email'],
            approval_request_id=log_data.get('approval_request_id'),
            action=DeactivationAction[log_data['action']],
            method=ExecutionMethod[log_data['method']] if log_data.get('method') else None,
            status=log_data['status'],
            error_message=log_data.get('error_message'),
            performed_by=log_data.get('performed_by'),
            reason=log_data.get('reason'),
            okta_status_at_time=log_data.get('okta_status_at_time'),
            netsuite_status_before=log_data.get('netsuite_status_before'),
            netsuite_status_after=log_data.get('netsuite_status_after'),
            log_metadata=log_data.get('log_metadata')
        )

        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)

        logger.info(f"Created deactivation log for {log.email}: {log.action} - {log.status}")
        return log

    def get_log_by_id(self, log_id: str) -> Optional[DeactivationLog]:
        """Get log by UUID"""
        return self.session.query(DeactivationLog).filter(
            DeactivationLog.id == log_id
        ).first()

    def get_logs_by_email(self, email: str, limit: Optional[int] = None) -> List[DeactivationLog]:
        """Get all logs for a specific email"""
        query = self.session.query(DeactivationLog).filter(
            DeactivationLog.email == email
        ).order_by(desc(DeactivationLog.performed_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_logs_by_approval(self, approval_request_id: str) -> List[DeactivationLog]:
        """Get all logs for a specific approval request"""
        return self.session.query(DeactivationLog).filter(
            DeactivationLog.approval_request_id == approval_request_id
        ).order_by(DeactivationLog.performed_at).all()

    def get_logs_by_action(
        self,
        action: DeactivationAction,
        limit: Optional[int] = None
    ) -> List[DeactivationLog]:
        """Get logs by action type"""
        query = self.session.query(DeactivationLog).filter(
            DeactivationLog.action == action
        ).order_by(desc(DeactivationLog.performed_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_logs_by_status(
        self,
        status: str,
        limit: Optional[int] = None
    ) -> List[DeactivationLog]:
        """Get logs by status (SUCCESS, FAILED, PENDING)"""
        query = self.session.query(DeactivationLog).filter(
            DeactivationLog.status == status
        ).order_by(desc(DeactivationLog.performed_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_failed_deactivations(self, hours: Optional[int] = None) -> List[DeactivationLog]:
        """Get failed deactivation attempts"""
        query = self.session.query(DeactivationLog).filter(
            DeactivationLog.status == 'FAILED'
        )

        if hours:
            cutoff_date = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(DeactivationLog.performed_at >= cutoff_date)

        return query.order_by(desc(DeactivationLog.performed_at)).all()

    def get_recent_logs(self, hours: int = 24, limit: Optional[int] = None) -> List[DeactivationLog]:
        """Get logs from the last N hours"""
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)
        query = self.session.query(DeactivationLog).filter(
            DeactivationLog.performed_at >= cutoff_date
        ).order_by(desc(DeactivationLog.performed_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None
    ) -> List[DeactivationLog]:
        """Get logs within a date range"""
        query = self.session.query(DeactivationLog).filter(
            and_(
                DeactivationLog.performed_at >= start_date,
                DeactivationLog.performed_at <= end_date
            )
        ).order_by(desc(DeactivationLog.performed_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_logs_by_performer(self, performed_by: str, limit: Optional[int] = None) -> List[DeactivationLog]:
        """Get logs by who performed the action"""
        query = self.session.query(DeactivationLog).filter(
            DeactivationLog.performed_by == performed_by
        ).order_by(desc(DeactivationLog.performed_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_deactivation_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get deactivation statistics for the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = self.session.query(DeactivationLog).filter(
            DeactivationLog.performed_at >= cutoff_date
        )

        total = query.count()

        # Count by action
        deactivations = query.filter(
            DeactivationLog.action == DeactivationAction.DEACTIVATE
        ).count()
        reactivations = query.filter(
            DeactivationLog.action == DeactivationAction.REACTIVATE
        ).count()

        # Count by status
        successful = query.filter(DeactivationLog.status == 'SUCCESS').count()
        failed = query.filter(DeactivationLog.status == 'FAILED').count()
        pending = query.filter(DeactivationLog.status == 'PENDING').count()

        # Count by method
        restlet = query.filter(DeactivationLog.method == ExecutionMethod.RESTLET).count()
        mapreduce = query.filter(DeactivationLog.method == ExecutionMethod.MAPREDUCE).count()
        manual = query.filter(DeactivationLog.method == ExecutionMethod.MANUAL).count()

        return {
            'period_days': days,
            'total_actions': total,
            'deactivations': deactivations,
            'reactivations': reactivations,
            'successful': successful,
            'failed': failed,
            'pending': pending,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'method_breakdown': {
                'RESTLET': restlet,
                'MAPREDUCE': mapreduce,
                'MANUAL': manual
            }
        }

    def get_user_deactivation_history(self, email: str) -> List[DeactivationLog]:
        """Get complete deactivation history for a user"""
        return self.session.query(DeactivationLog).filter(
            DeactivationLog.email == email
        ).order_by(DeactivationLog.performed_at).all()

    def bulk_create_logs(self, logs_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk create log entries"""
        created = 0
        errors = []

        for log_data in logs_data:
            try:
                self.create_log(log_data)
                created += 1
            except Exception as e:
                logger.error(f"Error creating log for {log_data.get('email')}: {str(e)}")
                errors.append({
                    'email': log_data.get('email'),
                    'error': str(e)
                })

        return {
            'created': created,
            'total': len(logs_data),
            'errors': errors
        }

    def get_logs_pending_completion(self, hours: int = 24) -> List[DeactivationLog]:
        """Get logs still in PENDING status after N hours"""
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)
        return self.session.query(DeactivationLog).filter(
            and_(
                DeactivationLog.status == 'PENDING',
                DeactivationLog.performed_at <= cutoff_date
            )
        ).order_by(DeactivationLog.performed_at).all()

    def update_log_status(
        self,
        log_id: str,
        status: str,
        error_message: Optional[str] = None,
        netsuite_status_after: Optional[str] = None
    ) -> Optional[DeactivationLog]:
        """Update log status"""
        log = self.get_log_by_id(log_id)

        if log:
            log.status = status

            if error_message:
                log.error_message = error_message

            if netsuite_status_after:
                log.netsuite_status_after = netsuite_status_after

            self.session.commit()
            self.session.refresh(log)
            logger.info(f"Updated log {log_id} status to {status}")
            return log

        return None

    def get_audit_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive audit report for a date range"""
        logs = self.get_logs_by_date_range(start_date, end_date)

        unique_users = set(log.email for log in logs)
        unique_performers = set(log.performed_by for log in logs if log.performed_by)

        # Group by approval request
        approval_groups = {}
        for log in logs:
            if log.approval_request_id:
                if log.approval_request_id not in approval_groups:
                    approval_groups[log.approval_request_id] = []
                approval_groups[log.approval_request_id].append(log)

        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_actions': len(logs),
            'unique_users_affected': len(unique_users),
            'unique_performers': len(unique_performers),
            'approval_batches': len(approval_groups),
            'statistics': self.get_deactivation_statistics(
                days=int((end_date - start_date).days)
            ),
            'logs': [
                {
                    'email': log.email,
                    'action': log.action.value,
                    'status': log.status,
                    'performed_at': log.performed_at.isoformat(),
                    'performed_by': log.performed_by,
                    'method': log.method.value if log.method else None
                }
                for log in logs
            ]
        }
