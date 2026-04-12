"""
STEMboost Core URL Patterns
"""
from django.urls import path
from . import views

urlpatterns = [
    # Landing & Auth
    path('',                 views.landing,           name='landing'),
    path('login/',           views.login_view,        name='login'),
    path('register/',        views.register_view,     name='register'),
    path('logout/',          views.logout_view,       name='logout'),

    # ── Learner ──────────────────────────────────────────────────────────────
    path('learner/',                           views.learner_dashboard,     name='learner_dashboard'),
    path('learner/chapter/<int:chapter_id>/',  views.chapter_view,          name='chapter_view'),
    path('learner/chat/',                      views.learner_chat,          name='learner_chat'),

    # ── Mentor ───────────────────────────────────────────────────────────────
    path('mentor/',                            views.mentor_dashboard,      name='mentor_dashboard'),
    path('mentor/chat/<int:learner_id>/',      views.mentor_chat,           name='mentor_chat'),

    # ── Admin ────────────────────────────────────────────────────────────────
    path('admin-dashboard/',                   views.admin_dashboard,       name='admin_dashboard'),
    path('admin-dashboard/delete-user/',       views.admin_delete_user,     name='admin_delete_user'),
    path('admin-dashboard/assign-mentor/<int:learner_id>/',
                                               views.admin_assign_mentor,   name='admin_assign_mentor'),
    path('admin-dashboard/course/add/',        views.admin_course_create,   name='admin_course_create'),
    path('admin-dashboard/course/<int:course_id>/edit/',
                                               views.admin_course_edit,     name='admin_course_edit'),
    path('admin-dashboard/course/<int:course_id>/delete/',
                                               views.admin_course_delete,   name='admin_course_delete'),
    path('admin-dashboard/course/<int:course_id>/chapter/add/',
                                               views.admin_chapter_create,  name='admin_chapter_create'),
    path('admin-dashboard/chapter/<int:chapter_id>/edit/',
                                               views.admin_chapter_edit,    name='admin_chapter_edit'),
    path('admin-dashboard/chapter/<int:chapter_id>/delete/',
                                               views.admin_chapter_delete,  name='admin_chapter_delete'),

    # ── AJAX API ─────────────────────────────────────────────────────────────
    path('api/messages/<int:partner_id>/',     views.api_messages,          name='api_messages'),
    path('api/messages/send/',                 views.api_send_message,      name='api_send_message'),
    path('api/chapter/<int:chapter_id>/complete/', views.mark_chapter_complete, name='mark_chapter_complete'),
]
