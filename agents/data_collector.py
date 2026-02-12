"""
Data Collection Agent - Fetches users and roles from NetSuite

This agent is responsible for:
1. Connecting to NetSuite via RESTlet
2. Fetching all active users with their roles
3. Storing data in PostgreSQL
4. Handling pagination and rate limits
5. Logging collection metrics
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from services.netsuite_client import NetSuiteClient

logger = logging.getLogger(__name__)


class DataCollectionAgent:
    """Agent for collecting user and role data from NetSuite"""

    def __init__(
        self,
        netsuite_client: Optional[NetSuiteClient] = None,
        llm_model: str = "claude-sonnet-4.5-20250929"
    ):
        """
        Initialize Data Collection Agent

        Args:
            netsuite_client: NetSuite client instance
            llm_model: Claude model to use for intelligent data processing
        """
        self.netsuite_client = netsuite_client or NetSuiteClient()
        self.llm = ChatAnthropic(model=llm_model, temperature=0)
        self.collection_stats = {
            'users_fetched': 0,
            'roles_found': 0,
            'permissions_collected': 0,
            'start_time': None,
            'end_time': None
        }

        logger.info(f"Data Collection Agent initialized with model: {llm_model}")

    @tool
    def fetch_users_from_netsuite(
        self,
        include_permissions: bool = True,
        status: str = 'ACTIVE'
    ) -> Dict[str, Any]:
        """
        Fetch all users and their roles from NetSuite

        Args:
            include_permissions: Whether to include detailed role permissions
            status: User status filter ('ACTIVE' or 'INACTIVE')

        Returns:
            Dictionary with users data and collection metadata
        """
        logger.info(f"Starting user collection from NetSuite (status={status})")
        self.collection_stats['start_time'] = datetime.now()

        try:
            # Fetch all users with pagination
            result = self.netsuite_client.get_all_users_paginated(
                include_permissions=include_permissions,
                status=status
            )

            if not result.get('success'):
                logger.error(f"Failed to fetch users: {result.get('error')}")
                return result

            users = result['data']['users']

            # Update statistics
            self.collection_stats['users_fetched'] = len(users)
            self.collection_stats['roles_found'] = sum(u.get('roles_count', 0) for u in users)

            if include_permissions:
                total_permissions = 0
                for user in users:
                    for role in user.get('roles', []):
                        total_permissions += len(role.get('permissions', []))
                self.collection_stats['permissions_collected'] = total_permissions

            self.collection_stats['end_time'] = datetime.now()
            duration = (self.collection_stats['end_time'] - self.collection_stats['start_time']).total_seconds()

            logger.info(
                f"Collection complete: {self.collection_stats['users_fetched']} users, "
                f"{self.collection_stats['roles_found']} roles, "
                f"{self.collection_stats['permissions_collected']} permissions in {duration:.2f}s"
            )

            return {
                'success': True,
                'data': users,
                'stats': self.collection_stats,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error during user collection: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Data collection failed'
            }

    def analyze_user_role_distribution(self, users: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use Claude to analyze the distribution of roles across users

        Args:
            users: List of user dictionaries

        Returns:
            Analysis results from Claude
        """
        logger.info(f"Analyzing role distribution for {len(users)} users")

        # Prepare summary data for Claude
        role_counts = {}
        users_with_multiple_roles = 0
        users_with_no_roles = 0

        for user in users:
            roles = user.get('roles', [])
            if len(roles) == 0:
                users_with_no_roles += 1
            elif len(roles) > 1:
                users_with_multiple_roles += 1

            for role in roles:
                role_name = role.get('role_name', 'Unknown')
                role_counts[role_name] = role_counts.get(role_name, 0) + 1

        # Sort roles by frequency
        top_roles = sorted(role_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a compliance analyst examining NetSuite user role distribution.
Analyze the data and identify potential concerns:
1. Users with multiple roles (potential SOD risks)
2. Unusual role combinations
3. Over-privileged roles
4. Users without roles (access issues)

Provide insights in JSON format."""),
            ("user", """Analyze this role distribution data:

Total users: {total_users}
Users with multiple roles: {multi_role_users}
Users with no roles: {no_role_users}

Top 10 roles by frequency:
{top_roles}

Provide analysis in this JSON format:
{{
    "summary": "Brief overview",
    "concerns": ["List of concerns"],
    "recommendations": ["List of recommendations"],
    "high_risk_patterns": ["Patterns that indicate SOD violations"]
}}""")
        ])

        chain = prompt | self.llm | JsonOutputParser()

        try:
            analysis = chain.invoke({
                "total_users": len(users),
                "multi_role_users": users_with_multiple_roles,
                "no_role_users": users_with_no_roles,
                "top_roles": "\n".join([f"{i+1}. {role}: {count} users" for i, (role, count) in enumerate(top_roles)])
            })

            logger.info("Role distribution analysis complete")
            return {
                'success': True,
                'analysis': analysis,
                'raw_stats': {
                    'total_users': len(users),
                    'users_with_multiple_roles': users_with_multiple_roles,
                    'users_with_no_roles': users_with_no_roles,
                    'unique_roles': len(role_counts),
                    'top_roles': top_roles
                }
            }

        except Exception as e:
            logger.error(f"Error during role analysis: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def collect_and_analyze(self) -> Dict[str, Any]:
        """
        Complete workflow: Fetch data from NetSuite and perform initial analysis

        Returns:
            Combined results of collection and analysis
        """
        logger.info("Starting complete data collection and analysis workflow")

        # Step 1: Fetch users
        collection_result = self.fetch_users_from_netsuite(
            include_permissions=True,
            status='ACTIVE'
        )

        if not collection_result.get('success'):
            return collection_result

        users = collection_result['data']

        # Step 2: Analyze distribution
        analysis_result = self.analyze_user_role_distribution(users)

        # Step 3: Combine results
        return {
            'success': True,
            'collection': {
                'users_count': len(users),
                'stats': collection_result['stats']
            },
            'analysis': analysis_result.get('analysis'),
            'raw_stats': analysis_result.get('raw_stats'),
            'timestamp': collection_result['timestamp']
        }

    def get_high_risk_users(self, users: List[Dict[str, Any]], min_roles: int = 3) -> List[Dict[str, Any]]:
        """
        Identify users with multiple roles (potential SOD risks)

        Args:
            users: List of user dictionaries
            min_roles: Minimum number of roles to be considered high risk

        Returns:
            List of high-risk users
        """
        high_risk = []

        for user in users:
            roles_count = user.get('roles_count', 0)
            if roles_count >= min_roles:
                high_risk.append({
                    'user_id': user.get('user_id'),
                    'name': user.get('name'),
                    'email': user.get('email'),
                    'roles_count': roles_count,
                    'roles': [r.get('role_name') for r in user.get('roles', [])]
                })

        logger.info(f"Found {len(high_risk)} high-risk users with {min_roles}+ roles")
        return high_risk

    def test_connection(self) -> bool:
        """Test NetSuite connection"""
        return self.netsuite_client.test_connection()


# Factory function
def create_data_collector() -> DataCollectionAgent:
    """Create a configured Data Collection Agent instance"""
    return DataCollectionAgent()
