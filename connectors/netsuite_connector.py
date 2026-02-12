"""
NetSuite Connector - Wraps existing NetSuite client for MCP integration
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_connector import BaseConnector
from services.netsuite_client import NetSuiteClient

logger = logging.getLogger(__name__)


class NetSuiteConnector(BaseConnector):
    """
    NetSuite connector for MCP integration

    Wraps the existing NetSuiteClient and provides async interface
    compatible with BaseConnector.
    """

    def __init__(self):
        super().__init__("netsuite")
        self.client = NetSuiteClient()
        logger.info("NetSuite connector initialized with existing client")

    async def test_connection(self) -> bool:
        """
        Test NetSuite connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            return self.client.test_connection()
        except Exception as e:
            logger.error(f"NetSuite connection test failed: {str(e)}")
            return False

    async def get_user_count(self) -> int:
        """
        Get total number of active users in NetSuite

        Returns:
            Number of active users
        """
        try:
            result = self.client.get_users_and_roles(
                limit=1,
                include_permissions=False
            )

            if result.get('success'):
                return result['data']['metadata'].get('total_users', 0)
            return 0

        except Exception as e:
            logger.error(f"Failed to get NetSuite user count: {str(e)}")
            return 0

    async def fetch_users_with_roles(
        self,
        include_permissions: bool = True,
        include_inactive: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch all users with their roles from NetSuite

        Args:
            include_permissions: Include detailed role permissions
            include_inactive: Include inactive users
            **kwargs: Additional parameters (subsidiary, department, etc.)

        Returns:
            List of user dictionaries with roles
        """
        logger.info(f"Fetching users from NetSuite (permissions={include_permissions})")

        try:
            # Use paginated fetch for all users
            result = self.client.get_all_users_paginated(
                include_permissions=include_permissions,
                status='ACTIVE' if not include_inactive else 'ALL',
                page_size=1000
            )

            if not result.get('success'):
                logger.error(f"Failed to fetch users: {result.get('error')}")
                return []

            users = result['data']['users']
            logger.info(f"Fetched {len(users)} users from NetSuite")

            return users

        except Exception as e:
            logger.error(f"Error fetching users from NetSuite: {str(e)}")
            raise

    async def search_user(
        self,
        search_value: str,
        search_type: str = 'both',
        include_permissions: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a specific user in NetSuite

        Args:
            search_value: Name or email to search for
            search_type: 'name', 'email', or 'both'
            include_permissions: Include role permissions

        Returns:
            User dictionary if found, None otherwise
        """
        logger.info(f"Searching NetSuite for user: {search_value}")

        try:
            result = self.client.search_users(
                search_value=search_value,
                search_type=search_type,
                include_permissions=include_permissions
            )

            if result.get('success') and result['data']['users']:
                return result['data']['users'][0]

            return None

        except Exception as e:
            logger.error(f"Error searching NetSuite user: {str(e)}")
            return None

    async def sync_to_database(
        self,
        users_data: List[Dict[str, Any]],
        user_repo
    ) -> List[Any]:
        """
        Sync NetSuite users to local database

        Args:
            users_data: List of user dictionaries from NetSuite
            user_repo: UserRepository instance

        Returns:
            List of synced User model objects
        """
        logger.info(f"Syncing {len(users_data)} NetSuite users to database")

        synced_users = []

        try:
            for user_data in users_data:
                # Extract user info
                email = user_data.get('email')
                if not email:
                    logger.warning(f"Skipping user without email: {user_data.get('name')}")
                    continue

                # Upsert user
                user = user_repo.upsert_user(
                    name=user_data.get('name', ''),
                    email=email,
                    department=user_data.get('department'),
                    is_active=user_data.get('is_active', True),
                    source_system='netsuite',
                    job_function=user_data.get('job_function'),
                    business_unit=user_data.get('business_unit')
                )

                # Sync roles
                roles = user_data.get('roles', [])
                for role_data in roles:
                    role_name = role_data.get('role_name')
                    if not role_name:
                        continue

                    # Assign role to user
                    user_repo.assign_role(
                        user_id=user.id,
                        role_name=role_name,
                        source_system='netsuite',
                        permissions=role_data.get('permissions', [])
                    )

                synced_users.append(user)

            logger.info(f"Successfully synced {len(synced_users)} users to database")
            return synced_users

        except Exception as e:
            logger.error(f"Error syncing users to database: {str(e)}")
            raise

    def get_system_type(self) -> str:
        """Get system type"""
        return "ERP"

    async def get_last_sync_date(self, violation_repo) -> Optional[datetime]:
        """
        Get the date of the last sync/review

        Args:
            violation_repo: ViolationRepository instance

        Returns:
            Last sync datetime or None
        """
        try:
            # Get most recent violation for this system
            violations = violation_repo.get_all_violations()
            netsuite_violations = [
                v for v in violations
                if v.user and v.user.source_system == 'netsuite'
            ]

            if netsuite_violations:
                # Sort by detected_at and get most recent
                sorted_violations = sorted(
                    netsuite_violations,
                    key=lambda x: x.detected_at,
                    reverse=True
                )
                return sorted_violations[0].detected_at

            return None

        except Exception as e:
            logger.error(f"Error getting last sync date: {str(e)}")
            return None
