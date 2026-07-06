"""Экспортируемые схемы запросов и ответов."""

from .auth import AuthLoginRequest, AuthStatusResponse
from .project import (
    ProjectCreateRequest,
    ProjectNotificationsSchema,
    ProjectResponse,
    ProjectStateResponse,
    StatusCreateRequest,
    StatusResponse,
)

__all__ = [
    "AuthLoginRequest",
    "AuthStatusResponse",
    "ProjectCreateRequest",
    "ProjectNotificationsSchema",
    "ProjectResponse",
    "ProjectStateResponse",
    "StatusCreateRequest",
    "StatusResponse",
]
