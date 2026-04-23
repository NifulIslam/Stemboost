"""
core/views/learner.py
─────────────────────
Learner-role views: dashboard, chapter reading, mentor chat.

HTTP concerns only; all business logic is delegated to the service layer.
"""

from django.contrib import messages as flash
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import Chapter, Course
from ..services import CommerceService, MessageService, ProgressService
from .decorators import role_required


# ── Learner Dashboard ─────────────────────────────────────────────────────────

@role_required("learner")
def learner_dashboard(request):
    """
    Show:
    - My Courses: enrolled courses with progress tracking.
    - Course Catalogue: all available courses for browsing/enrolling/purchasing.
    Supports optional catalogue search via GET ?q=.
    """
    learner = request.user
    query   = request.GET.get("q", "").strip()

    # Enrolled courses (shown with progress bars)
    enrolled_snapshot = ProgressService.build_enrolled_courses_snapshot(learner)
    stats             = ProgressService.compute_overall_stats(enrolled_snapshot)
    mentor            = MessageService.get_assigned_mentor(learner)

    # All courses for catalogue browse/search
    catalogue_qs = Course.objects.all()
    if query:
        catalogue_qs = catalogue_qs.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    enrolled_ids    = CommerceService.get_enrolled_course_ids(learner)
    cart_course_ids = set(learner.cart_items.values_list("course_id", flat=True))
    cart_count      = CommerceService.get_cart_count(learner)

    catalogue = [
        {
            "id":            course.id,
            "title":         course.title,
            "description":   course.description,
            "price":         course.price,
            "is_free":       course.price == 0,
            "chapter_count": course.get_chapter_count(),
            "is_enrolled":   course.id in enrolled_ids,
            "in_cart":       course.id in cart_course_ids,
        }
        for course in catalogue_qs
    ]

    return render(request, "core/dashboard_learner.html", {
        "page_name":        "Learner Dashboard",
        "user":             learner,
        "enrolled_courses": enrolled_snapshot,
        "catalogue":        catalogue,
        "query":            query,
        "mentor":           mentor,
        "cart_count":       cart_count,
        **stats,
    })


# ── Chapter View ──────────────────────────────────────────────────────────────

@role_required("learner")
def chapter_view(request, chapter_id: int):
    """
    Render a single chapter page with text content, optional image, and
    Read Aloud controls. Only enrolled learners may access chapters.
    """
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    learner = request.user

    # Enrollment gate: must be enrolled to read chapters
    if not CommerceService.is_enrolled(learner, chapter.course):
        flash.error(
            request,
            f'Please enroll in "{chapter.course.title}" to access its chapters.'
        )
        return redirect("learner_dashboard")

    course_chapters = list(chapter.course.chapters.order_by("order", "id"))
    current_index   = next(
        (i for i, ch in enumerate(course_chapters) if ch.id == chapter.id), 0
    )
    is_completed = chapter.id in ProgressService.get_completed_chapter_ids(learner)

    return render(request, "core/chapter_view.html", {
        "page_name":    f"Chapter: {chapter.title}",
        "chapter":      chapter,
        "course":       chapter.course,
        "is_completed": is_completed,
        "prev_chapter": course_chapters[current_index - 1] if current_index > 0 else None,
        "next_chapter": (
            course_chapters[current_index + 1]
            if current_index < len(course_chapters) - 1 else None
        ),
        "user": learner,
    })


# ── Mark Chapter Complete (AJAX) ──────────────────────────────────────────────

@require_POST
@login_required
def mark_chapter_complete(request, chapter_id: int):
    """
    Idempotent AJAX endpoint: record a chapter completion and return the
    updated course progress percentage. Only learners may call this.
    """
    if request.user.role != "learner":
        return JsonResponse({"error": "Forbidden"}, status=403)

    chapter  = get_object_or_404(Chapter, pk=chapter_id)
    progress = ProgressService.mark_chapter_complete(request.user, chapter)
    return JsonResponse({"progress": progress, "ok": True})


# ── Learner Chat ──────────────────────────────────────────────────────────────

@role_required("learner")
def learner_chat(request):
    """
    Direct chat between the learner and their assigned mentor.
    Shows a 'no mentor' placeholder if no assignment exists.
    """
    learner = request.user
    mentor  = MessageService.get_assigned_mentor(learner)

    if not mentor:
        return render(request, "core/chat.html", {
            "page_name": "Chat",
            "user":      learner,
            "partner":   None,
            "messages":  [],
            "no_mentor": True,
        })

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            MessageService.send_message(
                sender=learner, receiver=mentor, content=content
            )
        return redirect("learner_chat")

    return render(request, "core/chat.html", {
        "page_name": "Chat with Mentor",
        "user":      learner,
        "partner":   mentor,
        "messages":  MessageService.get_thread(learner, mentor),
        "no_mentor": False,
    })
