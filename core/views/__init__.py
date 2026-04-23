"""
core/views/__init__.py
──────────────────────
Re-exports every view callable so that core/urls.py can continue using
``from . import views`` and refer to views as ``views.landing``, etc.

This flat re-export is intentional: it keeps urls.py unchanged and avoids
breaking any existing bookmarks or reverse-URL lookups while still giving us
a clean module structure internally.
"""

# Auth
from .auth import landing, login_view, logout_view, register_view  # noqa: F401

# Learner
from .learner import (  # noqa: F401
    chapter_view,
    learner_chat,
    learner_dashboard,
    mark_chapter_complete,
)

# Mentor
from .mentor import (  # noqa: F401
    mentor_chat,
    mentor_dashboard,
    mentor_learner_progress,
)

# Admin
from .admin import (  # noqa: F401
    admin_assign_mentor,
    admin_chapter_create,
    admin_chapter_delete,
    admin_chapter_edit,
    admin_course_create,
    admin_course_delete,
    admin_course_edit,
    admin_dashboard,
    admin_delete_user,
)

# Commerce
from .commerce import (  # noqa: F401
    cart_add,
    cart_remove,
    cart_view,
    checkout_cart,
    checkout_single,
    enroll_free,
    transaction_result,
)

# API
from .api import api_messages, api_send_message  # noqa: F401
