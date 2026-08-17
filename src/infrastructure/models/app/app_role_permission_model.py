"""Role-permission association table alias kept in a dedicated file for schema parity."""

from .app_role_model import role_permissions

__all__ = ["role_permissions"]
