"""Web Alarm Workspace core package."""

from .models import SCHEMA_VERSION
from .workspace_registry import WorkspaceRegistry, WorkspaceRegistryError

__all__ = ["SCHEMA_VERSION", "WorkspaceRegistry", "WorkspaceRegistryError"]
