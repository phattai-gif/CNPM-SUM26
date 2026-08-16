"""Repository-facing user model exports.

This module intentionally does not define a second SQLAlchemy model. The app uses
one canonical model source under infrastructure.models.app to avoid duplicate ORM
metadata registration and schema drift.
"""

from infrastructure.models.app import UserModel

__all__ = ["UserModel"]
