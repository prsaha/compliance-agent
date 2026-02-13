"""
Autonomous Data Collection Agent

Continuously syncs user, role, and permission data from external systems
to the local database, ensuring data is always fresh and complete.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from models.database_config import DatabaseConfig
from repositories.user_repository import UserRepository
from repositories.role_repository import RoleRepository
from repositories.sync_metadata_repository import SyncMetadataRepository
from agents.analyzer import SODAnalysisAgent
from connectors.netsuite_connector import NetSuiteConnector

logger = logging.getLogger(__name__)


class DataCollectionAgent:
    """
    Autonomous agent for syncing data from external systems to PostgreSQL

    Responsibilities:
    1. Schedule and execute periodic data syncs
    2. Track sync metadata and metrics
    3. Handle errors and retries
    4. Trigger SOD analysis after syncs
    5. Send alerts on failures
    """

    def __init__(
        self,
        db_config: Optional[DatabaseConfig] = None,
        enable_scheduler: bool = True
    ):
        """
        Initialize the data collection agent

        Args:
            db_config: Database configuration (creates new if None)
            enable_scheduler: Whether to enable background scheduler
        """
        logger.info("Initializing DataCollectionAgent...")

        # Database setup
        self.db_config = db_config or DatabaseConfig()
        self.session = self.db_config.get_session()

        # Repositories
        self.user_repo = UserRepository(self.session)
        self.role_repo = RoleRepository(self.session)
        self.sync_repo = SyncMetadataRepository(self.session)

        # Connectors
        self.connectors = {
            'netsuite': NetSuiteConnector()
        }

        # SOD Analysis Agent
        from repositories.violation_repository import ViolationRepository
        from repositories.sod_rule_repository import SODRuleRepository

        self.violation_repo = ViolationRepository(self.session)
        self.rule_repo = SODRuleRepository(self.session)
        self.analyzer = SODAnalysisAgent(
            user_repo=self.user_repo,
            role_repo=self.role_repo,
            violation_repo=self.violation_repo,
            sod_rule_repo=self.rule_repo
        )

        # Scheduler
        self.scheduler = BackgroundScheduler() if enable_scheduler else None
        self.is_running = False

        logger.info("DataCollectionAgent initialized successfully")

    def start(self):
        """
        Start the autonomous collection agent with scheduled jobs
        """
        if not self.scheduler:
            logger.warning("Scheduler not enabled, cannot start scheduled jobs")
            return

        logger.info("Starting DataCollectionAgent scheduler...")

        # Schedule full sync: Daily at 2 AM
        self.scheduler.add_job(
            func=self.full_sync,
            trigger=CronTrigger(hour=2, minute=0),
            id='full_sync_daily',
            name='Full Sync (Daily 2 AM)',
            replace_existing=True
        )

        # Schedule incremental sync: Every hour
        self.scheduler.add_job(
            func=self.incremental_sync,
            trigger=IntervalTrigger(hours=1),
            id='incremental_sync_hourly',
            name='Incremental Sync (Hourly)',
            replace_existing=True
        )

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        logger.info("✅ DataCollectionAgent started successfully")
        logger.info("   • Full sync: Daily at 2:00 AM")
        logger.info("   • Incremental sync: Every hour")

    def stop(self):
        """Stop the scheduler and cleanup"""
        if self.scheduler and self.is_running:
            logger.info("Stopping DataCollectionAgent...")
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("✅ DataCollectionAgent stopped")

    def full_sync(self, system_name: str = 'netsuite', triggered_by: str = 'scheduler') -> Dict[str, Any]:
        """
        Perform full sync of all data from external system

        Args:
            system_name: System to sync (default: 'netsuite')
            triggered_by: Who triggered the sync

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting FULL sync for {system_name}")
        start_time = datetime.utcnow()

        # Create sync record
        sync = self.sync_repo.create_sync({
            'sync_type': 'full',
            'system_name': system_name,
            'status': 'pending',
            'started_at': start_time,
            'triggered_by': triggered_by
        })

        try:
            # Update status to running
            self.sync_repo.update_sync(str(sync.id), {'status': 'running'})

            # Get connector
            connector = self.connectors.get(system_name)
            if not connector:
                raise ValueError(f"No connector found for system: {system_name}")

            # Step 1: Fetch ALL users from external system
            logger.info(f"Fetching all users from {system_name}...")
            users_data = connector.fetch_users_with_roles_sync(
                include_permissions=True,
                include_inactive=True  # Include inactive users
            )

            users_fetched = len(users_data)
            logger.info(f"✅ Fetched {users_fetched} users from {system_name}")

            # Step 2: Sync to database
            logger.info(f"Syncing {users_fetched} users to database...")
            synced_users = connector.sync_to_database_sync(
                users_data,
                self.user_repo,
                self.role_repo
            )

            users_synced = len(synced_users)
            logger.info(f"✅ Synced {users_synced} users to database")

            # Count roles synced
            total_roles = sum(len(u.user_roles) for u in synced_users)

            # Step 3: Create compliance scan record for SOD analysis
            from models.database import ComplianceScan, ScanStatus

            compliance_scan = ComplianceScan(
                scan_type='AUTOMATED',
                status=ScanStatus.PENDING,
                triggered_by=triggered_by,
                started_at=datetime.utcnow(),
                scan_metadata={
                    'sync_id': str(sync.id),
                    'system_name': system_name,
                    'users_to_scan': users_synced
                }
            )
            self.session.add(compliance_scan)
            self.session.commit()
            self.session.refresh(compliance_scan)

            logger.info(f"Created compliance scan record: {compliance_scan.id}")

            # Step 4: Run SOD analysis with proper scan_id
            logger.info(f"Running SOD analysis on {users_synced} users...")
            compliance_scan.status = ScanStatus.IN_PROGRESS
            self.session.commit()

            analysis_result = self.analyzer.analyze_all_users(scan_id=str(compliance_scan.id))

            violations_detected = 0
            if analysis_result.get('success'):
                violations_detected = len(analysis_result.get('violations', []))
                logger.info(f"✅ Detected {violations_detected} violations")

                # Update compliance scan with results
                compliance_scan.status = ScanStatus.COMPLETED
                compliance_scan.completed_at = datetime.utcnow()
                compliance_scan.users_scanned = users_synced
                compliance_scan.violations_found = violations_detected

                # Count by severity
                violations_list = analysis_result.get('violations', [])
                compliance_scan.violations_critical = sum(1 for v in violations_list if v.get('severity') == 'CRITICAL')
                compliance_scan.violations_high = sum(1 for v in violations_list if v.get('severity') == 'HIGH')
                compliance_scan.violations_medium = sum(1 for v in violations_list if v.get('severity') == 'MEDIUM')
                compliance_scan.violations_low = sum(1 for v in violations_list if v.get('severity') == 'LOW')

                self.session.commit()
            else:
                logger.error(f"SOD analysis failed: {analysis_result.get('error')}")

                # Mark scan as failed
                compliance_scan.status = ScanStatus.FAILED
                compliance_scan.completed_at = datetime.utcnow()
                compliance_scan.error_message = str(analysis_result.get('error'))
                self.session.commit()

            # Step 5: Mark sync as successful
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            self.sync_repo.update_sync(str(sync.id), {
                'status': 'success',
                'completed_at': end_time,
                'users_fetched': users_fetched,
                'users_synced': users_synced,
                'roles_synced': total_roles,
                'violations_detected': violations_detected,
                'metadata': {
                    'analysis_success': analysis_result.get('success', False),
                    'users_analyzed': analysis_result.get('stats', {}).get('users_analyzed', 0),
                    'compliance_scan_id': str(compliance_scan.id)
                }
            })

            logger.info(f"✅ Full sync completed successfully in {duration:.2f}s")

            return {
                'success': True,
                'sync_id': str(sync.id),
                'scan_id': str(compliance_scan.id),
                'duration': duration,
                'users_fetched': users_fetched,
                'users_synced': users_synced,
                'roles_synced': total_roles,
                'violations_detected': violations_detected
            }

        except Exception as e:
            logger.error(f"Full sync failed: {str(e)}", exc_info=True)

            # Mark sync as failed
            self.sync_repo.update_sync(str(sync.id), {
                'status': 'failed',
                'completed_at': datetime.utcnow(),
                'error_message': str(e)
            })

            # Send alert (implement as needed)
            self._send_alert(f"Full sync failed for {system_name}: {str(e)}")

            return {
                'success': False,
                'sync_id': str(sync.id),
                'error': str(e)
            }

    def incremental_sync(self, system_name: str = 'netsuite', triggered_by: str = 'scheduler') -> Dict[str, Any]:
        """
        Perform incremental sync (only changed data since last sync)

        Args:
            system_name: System to sync
            triggered_by: Who triggered the sync

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting INCREMENTAL sync for {system_name}")

        # Get last successful sync
        last_sync = self.sync_repo.get_last_successful_sync(system_name)

        # If no previous sync or too old, do full sync instead
        if not last_sync:
            logger.info("No previous sync found, performing full sync instead")
            return self.full_sync(system_name, triggered_by)

        hours_since_last = (datetime.utcnow() - last_sync.completed_at).total_seconds() / 3600
        if hours_since_last > 24:
            logger.info(f"Last sync was {hours_since_last:.1f} hours ago, performing full sync")
            return self.full_sync(system_name, triggered_by)

        # For now, incremental sync falls back to full sync
        # TODO: Implement true incremental sync with lastModifiedDate filter
        logger.info("Incremental sync not yet implemented, performing full sync")
        return self.full_sync(system_name, triggered_by)

    def manual_sync(self, system_name: str = 'netsuite', sync_type: str = 'full') -> Dict[str, Any]:
        """
        Manually trigger a sync

        Args:
            system_name: System to sync
            sync_type: Type of sync ('full' or 'incremental')

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Manual sync triggered: {sync_type} sync for {system_name}")

        if sync_type == 'full':
            return self.full_sync(system_name, triggered_by='manual')
        else:
            return self.incremental_sync(system_name, triggered_by='manual')

    def get_sync_status(self, system_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current sync status and recent history

        Args:
            system_name: Optional system filter

        Returns:
            Dictionary with status information
        """
        recent_syncs = self.sync_repo.get_recent_syncs(system_name, limit=10)
        last_success = self.sync_repo.get_last_successful_sync(
            system_name or 'netsuite'
        )

        stats = self.sync_repo.get_sync_statistics(
            system_name or 'netsuite',
            days=7
        )

        return {
            'is_running': self.is_running,
            'last_successful_sync': {
                'completed_at': last_success.completed_at.isoformat() if last_success else None,
                'duration': last_success.duration_seconds if last_success else None,
                'users_synced': last_success.users_synced if last_success else 0
            } if last_success else None,
            'recent_syncs': [
                {
                    'id': str(s.id),
                    'type': s.sync_type.value,
                    'status': s.status.value,
                    'started_at': s.started_at.isoformat(),
                    'duration': s.duration_seconds,
                    'users_synced': s.users_synced
                }
                for s in recent_syncs
            ],
            'statistics_7d': stats
        }

    def _send_alert(self, message: str):
        """
        Send alert notification (Slack, email, etc.)

        Args:
            message: Alert message
        """
        # TODO: Implement alert mechanism
        logger.warning(f"ALERT: {message}")
        # Could integrate with:
        # - Slack webhook
        # - Email via SMTP
        # - PagerDuty
        # - etc.


# Global instance
_agent_instance: Optional[DataCollectionAgent] = None


def get_collection_agent() -> DataCollectionAgent:
    """
    Get or create global collection agent instance (singleton)

    Returns:
        DataCollectionAgent instance
    """
    global _agent_instance

    if _agent_instance is None:
        _agent_instance = DataCollectionAgent(enable_scheduler=True)

    return _agent_instance


def start_collection_agent():
    """Start the global collection agent"""
    agent = get_collection_agent()
    if not agent.is_running:
        agent.start()
    return agent


def stop_collection_agent():
    """Stop the global collection agent"""
    global _agent_instance
    if _agent_instance and _agent_instance.is_running:
        _agent_instance.stop()
