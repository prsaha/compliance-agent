"""
Compliance Orchestrator - Coordinates agents and connectors for MCP

This orchestrator sits between the MCP server and the existing compliance agents,
routing requests to appropriate components and aggregating results.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

# Import existing agents
from agents.analyzer import SODAnalysisAgent
from agents.notifier import NotificationAgent
from agents.knowledge_base_pgvector import KnowledgeBaseAgentPgvector

# Import connectors
from connectors.netsuite_connector import NetSuiteConnector

# Import repositories
from repositories.user_repository import UserRepository
from repositories.role_repository import RoleRepository
from repositories.violation_repository import ViolationRepository
from repositories.sod_rule_repository import SODRuleRepository

# Import database
from models.database_config import DatabaseConfig

logger = logging.getLogger(__name__)


class ComplianceOrchestrator:
    """
    Orchestrates compliance operations across agents and connectors

    This class coordinates:
    - Data fetching from external systems (NetSuite, Okta)
    - SOD analysis via AnalysisAgent
    - AI-powered analysis via NotificationAgent
    - Vector search via KnowledgeBaseAgent
    - Result aggregation and formatting
    """

    def __init__(self):
        """Initialize orchestrator with database, agents, and connectors"""
        logger.info("Initializing ComplianceOrchestrator...")

        # Initialize database
        self.db_config = DatabaseConfig()
        self.session = self.db_config.get_session()

        # Initialize repositories
        self.user_repo = UserRepository(self.session)
        self.role_repo = RoleRepository(self.session)
        self.violation_repo = ViolationRepository(self.session)
        self.rule_repo = SODRuleRepository(self.session)

        # Initialize agents
        self.analysis_agent = SODAnalysisAgent(
            user_repo=self.user_repo,
            role_repo=self.role_repo,
            violation_repo=self.violation_repo,
            sod_rule_repo=self.rule_repo
        )
        self.notifier_agent = NotificationAgent(
            violation_repo=self.violation_repo,
            user_repo=self.user_repo,
            enable_cache=True  # Enable Redis caching
        )
        self.kb_agent = KnowledgeBaseAgentPgvector(
            session=self.session,
            sod_rule_repo=self.rule_repo
        )

        # Initialize connectors
        self.connectors = {
            "netsuite": NetSuiteConnector(),
            # Add more connectors as implemented
            # "okta": OktaConnector(),
            # "salesforce": SalesforceConnector(),
        }

        logger.info("ComplianceOrchestrator initialized successfully")

    async def list_available_systems(self) -> List[Dict[str, Any]]:
        """
        List all configured systems with their status

        Returns:
            List of system dictionaries with status information
        """
        logger.info("Listing available systems...")
        systems = []

        for name, connector in self.connectors.items():
            try:
                # Test connection
                status = await connector.test_connection()

                # Get user count
                user_count = await connector.get_user_count() if status else 0

                # Get last review date
                last_review = await connector.get_last_sync_date(self.violation_repo)

                systems.append({
                    "name": name,
                    "type": connector.get_system_type(),
                    "status": "connected" if status else "disconnected",
                    "user_count": user_count,
                    "last_review": last_review.strftime("%Y-%m-%d %H:%M:%S") if last_review else "Never"
                })

                logger.info(f"System {name}: {status}, {user_count} users")

            except Exception as e:
                logger.error(f"Error checking system {name}: {str(e)}")
                systems.append({
                    "name": name,
                    "type": "unknown",
                    "status": "error",
                    "user_count": 0,
                    "last_review": "Error",
                    "error": str(e)
                })

        return systems

    async def perform_access_review(
        self,
        system_name: str,
        analysis_type: str = "sod_violations",
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Perform a comprehensive access review for a system

        Steps:
        1. Fetch users/roles from external system
        2. Sync to local database
        3. Run SOD analysis
        4. Generate AI recommendations (if requested)
        5. Return structured results

        Args:
            system_name: System to review (e.g., 'netsuite')
            analysis_type: Type of analysis ('sod_violations', 'excessive_permissions', etc.)
            include_recommendations: Generate AI-powered recommendations

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Starting access review for {system_name}")
        start_time = datetime.utcnow()

        # Step 1: Get connector
        connector = self.connectors.get(system_name)
        if not connector:
            raise ValueError(f"System not configured: {system_name}. Available: {list(self.connectors.keys())}")

        # Step 2: Test connection
        logger.info(f"Testing connection to {system_name}...")
        if not await connector.test_connection():
            raise ConnectionError(f"Cannot connect to {system_name}")

        # Step 3: Fetch data from external system
        logger.info(f"Fetching users from {system_name}...")
        users_data = await connector.fetch_users_with_roles(
            include_permissions=True
        )

        if not users_data:
            return {
                "system_name": system_name,
                "timestamp": start_time.isoformat(),
                "users_analyzed": 0,
                "total_violations": 0,
                "error": "No users found in system"
            }

        # Step 4: Sync to database
        logger.info(f"Syncing {len(users_data)} users to database...")
        synced_users = await connector.sync_to_database(users_data, self.user_repo)

        # Step 5: Run SOD analysis
        logger.info(f"Running SOD analysis for {len(synced_users)} users...")
        violations = self.analysis_agent.detect_sod_violations(
            user_ids=[u.id for u in synced_users]
        )

        # Step 6: Calculate statistics
        high_risk = len([v for v in violations if v.severity == "HIGH"])
        medium_risk = len([v for v in violations if v.severity == "MEDIUM"])
        low_risk = len([v for v in violations if v.severity == "LOW"])

        # Step 7: Get top violators
        user_violation_counts = {}
        for violation in violations:
            user_id = violation.user_id
            if user_id not in user_violation_counts:
                user = self.user_repo.get_user_by_id(user_id)
                user_violation_counts[user_id] = {
                    "user": user,
                    "count": 0,
                    "high_risk": 0,
                    "medium_risk": 0,
                    "low_risk": 0
                }
            user_violation_counts[user_id]["count"] += 1
            if violation.severity == "HIGH":
                user_violation_counts[user_id]["high_risk"] += 1
            elif violation.severity == "MEDIUM":
                user_violation_counts[user_id]["medium_risk"] += 1
            else:
                user_violation_counts[user_id]["low_risk"] += 1

        top_violators = sorted(
            [
                {
                    "name": v["user"].name,
                    "email": v["user"].email,
                    "violation_count": v["count"],
                    "high_risk": v["high_risk"],
                    "medium_risk": v["medium_risk"],
                    "low_risk": v["low_risk"]
                }
                for v in user_violation_counts.values()
            ],
            key=lambda x: (x["high_risk"], x["violation_count"]),
            reverse=True
        )

        # Step 8: Generate AI recommendations (if requested)
        recommendations = ""
        if include_recommendations and violations:
            logger.info("Generating AI recommendations...")
            recommendations = await self._generate_recommendations(
                system_name, violations, top_violators
            )

        # Step 9: Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        logger.info(f"Access review complete: {len(violations)} violations found in {execution_time:.2f}s")

        return {
            "system_name": system_name,
            "timestamp": start_time.isoformat(),
            "execution_time_seconds": round(execution_time, 2),
            "users_analyzed": len(synced_users),
            "total_violations": len(violations),
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "low_risk_count": low_risk,
            "top_violators": top_violators[:10],  # Top 10
            "recommendations": recommendations,
            "analysis_type": analysis_type
        }

    async def get_user_violations(
        self,
        system_name: str,
        user_identifier: str,
        include_ai_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed violations for a specific user

        Args:
            system_name: System name ('netsuite', 'okta', etc.)
            user_identifier: User email or ID
            include_ai_analysis: Include AI-powered risk analysis

        Returns:
            Dictionary with user violations and analysis
        """
        logger.info(f"Fetching violations for {user_identifier} in {system_name}")

        # Find user by email or ID
        user = self.user_repo.get_user_by_email(user_identifier)
        if not user:
            # Try by ID
            try:
                user = self.user_repo.get_user_by_id(user_identifier)
            except:
                pass

        if not user:
            raise ValueError(f"User not found: {user_identifier}")

        # Get violations
        violations = self.violation_repo.get_violations_by_user(user.id)

        # Get user roles
        roles = [ur.role.role_name for ur in user.user_roles]

        # Format violations
        formatted_violations = []
        for v in violations:
            formatted_violations.append({
                "id": str(v.id),
                "rule_name": v.rule.rule_name,
                "severity": v.severity,
                "description": v.rule.description,
                "risk_description": v.rule.risk,
                "status": v.status,
                "detected_at": v.detected_at.isoformat(),
                "conflicting_roles": [r.role_name for r in v.rule.conflicting_roles]
            })

        # Generate AI analysis (if requested)
        ai_analysis = ""
        if include_ai_analysis and violations:
            logger.info("Generating AI analysis for user violations...")
            ai_analysis = self.notifier_agent._generate_ai_analysis(
                user, violations, roles
            )

        return {
            "user_name": user.name,
            "email": user.email,
            "system": system_name,
            "roles": roles,
            "role_count": len(roles),
            "violation_count": len(violations),
            "violations": formatted_violations,
            "ai_analysis": ai_analysis,
            "department": user.department,
            "is_active": user.is_active
        }

    async def remediate_violation(
        self,
        violation_id: str,
        action: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Create remediation plan for a violation

        Args:
            violation_id: Violation UUID
            action: Remediation action type
            notes: Additional notes

        Returns:
            Remediation status dictionary
        """
        logger.info(f"Creating remediation for violation {violation_id}: {action}")

        # Get violation
        violation = self.violation_repo.get_violation_by_id(violation_id)
        if not violation:
            raise ValueError(f"Violation not found: {violation_id}")

        # Get user
        user = violation.user

        # TODO: Implement actual remediation actions
        # For now, return a structured response

        next_steps = []
        if action == "remove_role":
            next_steps = [
                f"Identify which role to remove from {user.name}",
                "Create ticket in ServiceNow for role removal",
                "Notify user's manager for approval",
                "Schedule role removal after approval"
            ]
        elif action == "request_approval":
            next_steps = [
                f"Send approval request to {user.name}'s manager",
                "Document business justification for current role assignment",
                "Set up compensating controls if approval granted",
                "Re-review in 90 days"
            ]
        elif action == "create_ticket":
            next_steps = [
                "Create ServiceNow ticket with violation details",
                "Assign to IT Security team",
                "Set priority based on risk level",
                "Track remediation progress"
            ]
        elif action == "notify_manager":
            next_steps = [
                f"Send notification to {user.name}'s manager",
                "Include violation details and risk assessment",
                "Request action within 7 days",
                "Escalate if no response"
            ]

        return {
            "status": "initiated",
            "violation_id": violation_id,
            "user_name": user.name,
            "user_email": user.email,
            "action": action,
            "ticket_id": f"REM-{violation_id[:8].upper()}",
            "notes": notes,
            "next_steps": next_steps,
            "created_at": datetime.utcnow().isoformat()
        }

    async def schedule_review(
        self,
        system_name: str,
        frequency: str,
        day_of_week: Optional[str] = None,
        time: Optional[str] = None,
        timezone: str = "America/Los_Angeles"
    ) -> Dict[str, Any]:
        """
        Schedule recurring compliance review

        Args:
            system_name: System to review
            frequency: 'daily', 'weekly', or 'monthly'
            day_of_week: Day for weekly reviews
            time: Time in HH:MM format
            timezone: IANA timezone

        Returns:
            Schedule confirmation dictionary
        """
        logger.info(f"Scheduling {frequency} review for {system_name}")

        # TODO: Implement actual scheduling with APScheduler or similar
        # For now, return a mock response

        schedule_desc = self._build_schedule_description(frequency, day_of_week, time)
        next_run = self._calculate_next_run(frequency, day_of_week, time, timezone)

        return {
            "status": "scheduled",
            "system_name": system_name,
            "frequency": frequency,
            "schedule_description": schedule_desc,
            "next_run": next_run,
            "timezone": timezone,
            "notification_channels": ["Email", "Claude UI"],
            "created_at": datetime.utcnow().isoformat()
        }

    async def get_violation_stats(
        self,
        systems: Optional[List[str]] = None,
        time_range: str = "month"
    ) -> Dict[str, Any]:
        """
        Get aggregate violation statistics

        Args:
            systems: List of systems to include (None = all)
            time_range: 'today', 'week', 'month', 'quarter', 'year'

        Returns:
            Statistics dictionary
        """
        logger.info(f"Fetching violation stats for {time_range}")

        # Get all violations
        all_violations = self.violation_repo.get_all_violations()

        # Filter by system if specified
        if systems:
            all_violations = [
                v for v in all_violations
                if v.user and v.user.source_system in systems
            ]

        # Calculate statistics
        total_violations = len(all_violations)
        high_risk = len([v for v in all_violations if v.severity == "HIGH"])
        medium_risk = len([v for v in all_violations if v.severity == "MEDIUM"])
        low_risk = len([v for v in all_violations if v.severity == "LOW"])

        # Get unique users
        unique_users = set(v.user_id for v in all_violations if v.user_id)
        total_users = len(unique_users)

        # Group by system
        by_system = {}
        for violation in all_violations:
            if violation.user:
                system = violation.user.source_system
                if system not in by_system:
                    by_system[system] = 0
                by_system[system] += 1

        by_system_list = [
            {"name": system, "violation_count": count}
            for system, count in by_system.items()
        ]

        return {
            "time_range": time_range,
            "system_count": len(by_system),
            "total_users": total_users,
            "total_violations": total_violations,
            "high_risk": high_risk,
            "high_risk_percent": round(high_risk / max(total_violations, 1) * 100, 1),
            "medium_risk": medium_risk,
            "medium_risk_percent": round(medium_risk / max(total_violations, 1) * 100, 1),
            "low_risk": low_risk,
            "low_risk_percent": round(low_risk / max(total_violations, 1) * 100, 1),
            "by_system": by_system_list,
            "trend_description": "Statistics for current period"
        }

    # Helper methods

    async def _generate_recommendations(
        self,
        system_name: str,
        violations: List,
        top_violators: List[Dict[str, Any]]
    ) -> str:
        """Generate AI-powered recommendations based on violations"""

        if not violations:
            return "No violations found - system is compliant."

        # Create summary for AI
        high_risk_count = len([v for v in violations if v.severity == "HIGH"])
        total_count = len(violations)
        top_3 = top_violators[:3]

        # Generate recommendations using existing NotificationAgent LLM
        prompt = f"""Based on the SOD compliance analysis of {system_name}:

Total Violations: {total_count}
High-Risk Violations: {high_risk_count}

Top Violators:
{chr(10).join([f"- {v['name']} ({v['email']}): {v['violation_count']} violations" for v in top_3])}

Provide 3-5 prioritized recommendations for remediation. Focus on:
1. Highest risk users/violations
2. Quick wins that reduce multiple violations
3. Process improvements to prevent future violations

Be specific and actionable."""

        try:
            # Use the same LLM as NotificationAgent
            response = self.notifier_agent.llm.generate([
                {"role": "user", "content": prompt}
            ])
            return response.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            return "Unable to generate AI recommendations at this time."

    def _build_schedule_description(
        self,
        frequency: str,
        day_of_week: Optional[str],
        time: Optional[str]
    ) -> str:
        """Build human-readable schedule description"""
        time_str = time or "09:00"

        if frequency == "daily":
            return f"Every day at {time_str}"
        elif frequency == "weekly":
            day = (day_of_week or "monday").capitalize()
            return f"Every {day} at {time_str}"
        elif frequency == "monthly":
            return f"First day of each month at {time_str}"

        return frequency

    def _calculate_next_run(
        self,
        frequency: str,
        day_of_week: Optional[str],
        time: Optional[str],
        timezone: str
    ) -> str:
        """Calculate next run timestamp (simplified)"""
        # TODO: Implement actual calculation with timezone support
        from datetime import timedelta

        now = datetime.utcnow()

        if frequency == "daily":
            next_run = now + timedelta(days=1)
        elif frequency == "weekly":
            next_run = now + timedelta(days=7)
        elif frequency == "monthly":
            next_run = now + timedelta(days=30)
        else:
            next_run = now + timedelta(days=1)

        return next_run.strftime("%Y-%m-%d %H:%M:%S") + f" {timezone}"
