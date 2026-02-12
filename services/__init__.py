"""Services package for external integrations"""

from .netsuite_client import NetSuiteClient, get_netsuite_client

__all__ = ['NetSuiteClient', 'get_netsuite_client']
