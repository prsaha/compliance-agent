"""
BaseRepository — Generic typed repository base class.

All concrete repositories should subclass BaseRepository[T] to inherit
standard CRUD, bulk-insert, and session-management patterns.

Usage:
    class ViolationRepository(BaseRepository[Violation]):
        model = Violation
        ...
"""

import logging
from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# SQLAlchemy model type variable
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Generic base repository providing standard CRUD operations.

    Subclasses must set the `model` class attribute to the SQLAlchemy model class.

    Example:
        class ViolationRepository(BaseRepository[Violation]):
            model = Violation
    """

    model: Type[T]

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_by_id(self, record_id: Any) -> Optional[T]:
        """Return a single record by its primary key, or None."""
        try:
            return self.session.query(self.model).get(record_id)
        except SQLAlchemyError as exc:
            logger.error(f"[{self.model.__name__}] get_by_id({record_id}) failed: {exc}")
            return None

    def get_all(self, limit: int = 1000, offset: int = 0) -> List[T]:
        """Return all records (with optional pagination)."""
        try:
            return (
                self.session.query(self.model)
                .offset(offset)
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as exc:
            logger.error(f"[{self.model.__name__}] get_all failed: {exc}")
            return []

    def count(self) -> int:
        """Return total row count."""
        try:
            return self.session.query(self.model).count()
        except SQLAlchemyError as exc:
            logger.error(f"[{self.model.__name__}] count failed: {exc}")
            return 0

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(self, instance: T) -> Optional[T]:
        """Add a pre-constructed model instance to the session and commit."""
        try:
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except SQLAlchemyError as exc:
            logger.error(f"[{self.model.__name__}] add failed: {exc}")
            self.session.rollback()
            return None

    def update(self) -> bool:
        """Flush pending changes and commit. Call after mutating instance attributes."""
        try:
            self.session.commit()
            return True
        except SQLAlchemyError as exc:
            logger.error(f"[{self.model.__name__}] update/commit failed: {exc}")
            self.session.rollback()
            return False

    def delete(self, instance: T) -> bool:
        """Delete a single record and commit."""
        try:
            self.session.delete(instance)
            self.session.commit()
            return True
        except SQLAlchemyError as exc:
            logger.error(f"[{self.model.__name__}] delete failed: {exc}")
            self.session.rollback()
            return False

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def bulk_create(self, mappings: List[Dict[str, Any]]) -> int:
        """
        Insert many rows in a single statement using bulk_insert_mappings.

        Args:
            mappings: List of dicts matching the model's column set.

        Returns:
            Number of rows inserted, or 0 on failure.
        """
        if not mappings:
            return 0
        try:
            self.session.bulk_insert_mappings(self.model, mappings)
            self.session.commit()
            logger.info(f"[{self.model.__name__}] bulk_create: inserted {len(mappings)} rows")
            return len(mappings)
        except SQLAlchemyError as exc:
            logger.error(f"[{self.model.__name__}] bulk_create failed: {exc}")
            self.session.rollback()
            return 0

    def bulk_update(self, mappings: List[Dict[str, Any]]) -> int:
        """
        Update many rows in a single statement using bulk_update_mappings.

        Each mapping must include the primary key field(s) plus the columns to update.

        Args:
            mappings: List of dicts with pk + updated fields.

        Returns:
            Number of rows updated, or 0 on failure.
        """
        if not mappings:
            return 0
        try:
            self.session.bulk_update_mappings(self.model, mappings)
            self.session.commit()
            logger.info(f"[{self.model.__name__}] bulk_update: updated {len(mappings)} rows")
            return len(mappings)
        except SQLAlchemyError as exc:
            logger.error(f"[{self.model.__name__}] bulk_update failed: {exc}")
            self.session.rollback()
            return 0
