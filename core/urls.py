"""
core/urls.py
────────────
URL patterns for the STEMboost core application.

Pattern groups
──────────────
- Public / Auth  : landing, login, register, logout
- Learner        : dashboard, chapter reading, chat
- Mentor         : dashboard, per-learner progress, chat
- Admin          : user management, course/chapter CRUD, mentor assignment
- AJAX API       : message polling/send, chapter-complete toggle
"""

from django.urls import path

from . import views

urlpatterns = [

    # ── Public / Auth ─────────────────────────────────────────────────────────
    path("",          views.landing,       name="landing"),
    path("login/",    views.login_view,    name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/",   views.logout_view,   name="logout"),

    # ── Learner ───────────────────────────────────────────────────────────────
    path("learner/",
         views.learner_dashboard,
         name="learner_dashboard"),

    path("learner/chapter/<int:chapter_id>/",
         views.chapter_view,
         name="chapter_view"),

    path("learner/chat/",
         views.learner_chat,
         name="learner_chat"),

    # ── Mentor ────────────────────────────────────────────────────────────────
    path("mentor/",
         views.mentor_dashboard,
         name="mentor_dashboard"),

    path("mentor/learner/<int:learner_id>/progress/",
         views.mentor_learner_progress,
         name="mentor_learner_progress"),

    path("mentor/chat/<int:learner_id>/",
         views.mentor_chat,
         name="mentor_chat"),

    # ── Admin ─────────────────────────────────────────────────────────────────
    path("admin-dashboard/",
         views.admin_dashboard,
         name="admin_dashboard"),

    path("admin-dashboard/delete-user/",
         views.admin_delete_user,
         name="admin_delete_user"),

    path("admin-dashboard/assign-mentor/<int:learner_id>/",
         views.admin_assign_mentor,
         name="admin_assign_mentor"),

    # Course CRUD
    path("admin-dashboard/course/add/",
         views.admin_course_create,
         name="admin_course_create"),

    path("admin-dashboard/course/<int:course_id>/edit/",
         views.admin_course_edit,
         name="admin_course_edit"),

    path("admin-dashboard/course/<int:course_id>/delete/",
         views.admin_course_delete,
         name="admin_course_delete"),

    # Chapter CRUD
    path("admin-dashboard/course/<int:course_id>/chapter/add/",
         views.admin_chapter_create,
         name="admin_chapter_create"),

    path("admin-dashboard/chapter/<int:chapter_id>/edit/",
         views.admin_chapter_edit,
         name="admin_chapter_edit"),

    path("admin-dashboard/chapter/<int:chapter_id>/delete/",
         views.admin_chapter_delete,
         name="admin_chapter_delete"),

    # ── AJAX API ──────────────────────────────────────────────────────────────
    path("api/messages/<int:partner_id>/",
         views.api_messages,
         name="api_messages"),

    path("api/messages/send/",
         views.api_send_message,
         name="api_send_message"),

    path("api/chapter/<int:chapter_id>/complete/",
         views.mark_chapter_complete,
         name="mark_chapter_complete"),

    # ── Commerce (Cart / Enrollment / Purchase) ───────────────────────────────
    path("learner/cart/",
         views.cart_view,
         name="cart_view"),

    path("learner/cart/add/<int:course_id>/",
         views.cart_add,
         name="cart_add"),

    path("learner/cart/remove/<int:course_id>/",
         views.cart_remove,
         name="cart_remove"),

    path("learner/enroll/<int:course_id>/",
         views.enroll_free,
         name="enroll_free"),

    path("learner/checkout/course/<int:course_id>/",
         views.checkout_single,
         name="checkout_single"),

    path("learner/checkout/cart/",
         views.checkout_cart,
         name="checkout_cart"),

    path("learner/transaction/<str:tx_ref>/",
         views.transaction_result,
         name="transaction_result"),
]
