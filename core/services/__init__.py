"""
core/services
─────────────
Service layer for STEMboost.

Import from here for convenience:

    from core.services import ProgressService, MessageService, CourseService, UserService, CommerceService
"""

from .commerce import CommerceService
from .course import CourseService
from .messaging import MessageService
from .progress import ProgressService
from .user import UserService

__all__ = [
    "CommerceService",
    "CourseService",
    "MessageService",
    "ProgressService",
    "UserService",
]
