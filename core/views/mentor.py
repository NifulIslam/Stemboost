"""
core/views/mentor.py
─────────────────────
Mentor-role views: dashboard, per-learner progress, and chat.

New feature: mentor_learner_progress
    A dedicated page showing a selected learner's progress across every
    enrolled course, including per-chapter completion status.
"""

from django.contrib import messages as flash
from django.shortcuts import get_object_or_404, redirect, render

from ..models import User
from ..services import MessageService, ProgressService, UserService
from .decorators import role_required


# ── Mentor Dashboard ──────────────────────────────────────────────────────────

@role_required("mentor")
def mentor_dashboard(request):
    """
    Show all learners assigned to this mentor, each with a Chat button and
    a View Progress button.
    """
    mentor   = request.user
    learners = UserService.get_assigned_learners(mentor)

    return render(request, "core/dashboard_mentor.html", {
        "page_name":     "Mentor Dashboard",
        "user":          mentor,
        "learners":      learners,
        "learner_count": len(learners),
    })


# ── Learner Progress (NEW) ────────────────────────────────────────────────────

@role_required("mentor")
def mentor_learner_progress(request, learner_id: int):
    """
    Display one assigned learner's progress across every course.

    For each course the page shows:
    - Overall progress percentage with a visual bar.
    - Each chapter listed with a ✅/○ completion indicator.

    Access is restricted: mentors can only view their own assigned learners.
    """
    mentor  = request.user
    learner = get_object_or_404(User, pk=learner_id, role="learner")

    # Authorization: confirm this learner is assigned to this mentor
    try:
        MessageService.assert_learner_assigned_to_mentor(mentor, learner)
    except PermissionError as exc:
        flash.error(request, str(exc))
        return redirect("mentor_dashboard")

    courses_snapshot = ProgressService.build_learner_progress_for_mentor(learner)
    stats            = ProgressService.compute_overall_stats(courses_snapshot)

    return render(request, "core/mentor_learner_progress.html", {
        "page_name": f"{learner.email} — Course Progress",
        "user":      mentor,
        "learner":   learner,
        "courses":   courses_snapshot,
        **stats,
    })


# ── Mentor Chat ───────────────────────────────────────────────────────────────

@role_required("mentor")
def mentor_chat(request, learner_id: int):
    """
    Direct chat between a mentor and one of their assigned learners.
    POST is a legacy form-submit fallback; AJAX send is preferred.
    """
    mentor  = request.user
    learner = get_object_or_404(User, pk=learner_id, role="learner")

    try:
        MessageService.assert_learner_assigned_to_mentor(mentor, learner)
    except PermissionError as exc:
        flash.error(request, str(exc))
        return redirect("mentor_dashboard")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            MessageService.send_message(
                sender=mentor, receiver=learner, content=content
            )
        return redirect("mentor_chat", learner_id=learner_id)

    return render(request, "core/chat.html", {
        "page_name": f"Chat with {learner.email}",
        "user":      mentor,
        "partner":   learner,
        "messages":  MessageService.get_thread(mentor, learner),
        "no_mentor": False,
    })
