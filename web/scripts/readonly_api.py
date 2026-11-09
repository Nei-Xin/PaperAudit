"""Compatibility entry point for the deployed read-only preview."""
from paperaudit.api.views import ReadOnlyApi, NotFound

__all__ = ["ReadOnlyApi", "NotFound"]
