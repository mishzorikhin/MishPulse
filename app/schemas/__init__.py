"""Экспортируемые схемы запросов и ответов."""

from .auth import AuthLoginRequest, AuthStatusResponse
from .project import (
    MaintenanceCleanupResponse,
    ProjectCreateRequest,
    ProjectNotificationsSchema,
    ProjectResponse,
    ProjectStateResponse,
    ProjectUpdateRequest,
    StatusCreateRequest,
    StatusResponse,
)

__all__ = [
    "AuthLoginRequest",
    "AuthStatusResponse",
    "MaintenanceCleanupResponse",
    "ProjectCreateRequest",
    "ProjectNotificationsSchema",
    "ProjectResponse",
    "ProjectStateResponse",
    "ProjectUpdateRequest",
    "StatusCreateRequest",
    "StatusResponse",
]
