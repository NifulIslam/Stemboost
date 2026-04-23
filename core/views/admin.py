"""
core/views/admin.py
────────────────────
Admin-role views: user management, course/chapter CRUD, mentor assignment.

Each view is kept thin:
- Input validation is done via Django Forms.
- Business logic (deletion rules, caption generation, etc.) lives in services.
- Flash messages are the only admin-feedback mechanism (no inline JSON).
"""

from django.contrib import messages as flash
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import ChapterForm, CourseForm
from ..models import Chapter, Course, User
from ..services import CourseService, UserService
from .decorators import role_required

# A module-level CourseService instance uses the default AI captioner.
# Swap it in tests via dependency injection.
_course_svc = CourseService()


# ── Admin Dashboard ───────────────────────────────────────────────────────────

@role_required("admin")
def admin_dashboard(request):
    """Overview: platform stats, learner/mentor table, course list."""
    all_users = User.objects.all().order_by("role", "date_joined")
    learners  = User.objects.filter(role="learner")
    mentors   = User.objects.filter(role="mentor")
    admins    = User.objects.filter(role="admin")
    courses   = Course.objects.all()

    return render(request, "core/dashboard_admin.html", {
        "page_name":      "Admin Dashboard",
        "user":           request.user,
        "all_users":      all_users,
        "learner_data":   UserService.build_learner_rows(learners),
        "mentors":        mentors,
        "courses":        courses,
        "total_users":    all_users.count(),
        "total_learners": learners.count(),
        "total_mentors":  mentors.count(),
        "total_admins":   admins.count(),
        "total_courses":  courses.count(),
    })


# ── User Deletion ─────────────────────────────────────────────────────────────

@role_required("admin")
@require_POST
def admin_delete_user(request):
    """
    Delete a user account.  Admin-protection and self-deletion rules are
    enforced by UserService.delete_user (raises PermissionError on violation).
    """
    raw_id = request.POST.get("delete_user_id", "")
    if not raw_id.isdigit():
        flash.error(request, "Invalid user ID.")
        return redirect("admin_dashboard")

    try:
        target = User.objects.get(pk=int(raw_id))
        email  = UserService.delete_user(actor=request.user, target=target)
        flash.success(request, f"User {email} has been removed.")
    except User.DoesNotExist:
        flash.error(request, "User not found.")
    except PermissionError as exc:
        flash.error(request, str(exc))

    return redirect("admin_dashboard")


# ── Mentor Assignment ─────────────────────────────────────────────────────────

@role_required("admin")
@require_POST
def admin_assign_mentor(request, learner_id: int):
    """Assign (or re-assign) a mentor to a learner."""
    learner   = get_object_or_404(User, pk=learner_id, role="learner")
    mentor_id = request.POST.get("mentor_id", "").strip()

    if not mentor_id or not mentor_id.isdigit():
        flash.error(request, "Please select a valid mentor.")
        return redirect("admin_dashboard")

    mentor = get_object_or_404(User, pk=int(mentor_id), role="mentor")

    try:
        UserService.assign_mentor(
            learner=learner, mentor=mentor, assigned_by=request.user
        )
        flash.success(
            request,
            f"{learner.email} has been assigned to mentor {mentor.email}.",
        )
    except ValueError as exc:
        flash.error(request, str(exc))

    return redirect("admin_dashboard")


# ── Course Management ─────────────────────────────────────────────────────────

@role_required("admin")
def admin_course_create(request):
    """Render and process the Create Course form."""
    form = CourseForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            course = _course_svc.create_course(
                title=form.cleaned_data["title"],
                description=form.cleaned_data.get("description", ""),
                created_by=request.user,
                price=form.cleaned_data.get("price", 0),
            )
            flash.success(request, f'Course "{course.title}" created.')
            return redirect("admin_course_edit", course_id=course.id)
        except ValueError as exc:
            flash.error(request, str(exc))

    return render(request, "core/course_form.html", {
        "page_name": "Create Course",
        "form":      form,
        "action":    "Create",
        "user":      request.user,
    })


@role_required("admin")
def admin_course_edit(request, course_id: int):
    """Render and process the Edit Course form; also lists that course's chapters."""
    course = get_object_or_404(Course, pk=course_id)
    form   = CourseForm(request.POST or None, instance=course)

    if request.method == "POST" and form.is_valid():
        try:
            _course_svc.update_course(
                course=course,
                title=form.cleaned_data["title"],
                description=form.cleaned_data.get("description", ""),
                price=form.cleaned_data.get("price", 0),
            )
            flash.success(request, "Course updated.")
            return redirect("admin_course_edit", course_id=course.id)
        except ValueError as exc:
            flash.error(request, str(exc))

    return render(request, "core/course_form.html", {
        "page_name": f"Edit Course — {course.title}",
        "form":      form,
        "course":    course,
        "chapters":  course.chapters.order_by("order", "id"),
        "action":    "Save Changes",
        "user":      request.user,
    })


@role_required("admin")
@require_POST
def admin_course_delete(request, course_id: int):
    """Delete a course and all its chapters."""
    course = get_object_or_404(Course, pk=course_id)
    title  = _course_svc.delete_course(course)
    flash.success(request, f'Course "{title}" deleted.')
    return redirect("admin_dashboard")


# ── Chapter Management ────────────────────────────────────────────────────────

@role_required("admin")
def admin_chapter_create(request, course_id: int):
    """Add a new chapter to a course.  Triggers AI image captioning on upload."""
    course = get_object_or_404(Course, pk=course_id)
    form   = ChapterForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        try:
            chapter = _course_svc.create_chapter(
                course=course,
                title=form.cleaned_data["title"],
                content=form.cleaned_data["content"],
                order=form.cleaned_data.get("order", 0),
                image=request.FILES.get("image"),
            )
            flash.success(request, f'Chapter "{chapter.title}" added.')
            return redirect("admin_course_edit", course_id=course.id)
        except ValueError as exc:
            flash.error(request, str(exc))

    return render(request, "core/chapter_form.html", {
        "page_name": "Add Chapter",
        "form":      form,
        "course":    course,
        "action":    "Add Chapter",
        "user":      request.user,
    })


@role_required("admin")
def admin_chapter_edit(request, chapter_id: int):
    """Edit an existing chapter.  Re-captions image only when a new file is uploaded."""
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    form    = ChapterForm(request.POST or None, request.FILES or None, instance=chapter)

    if request.method == "POST" and form.is_valid():
        try:
            new_image = request.FILES.get("image") or None
            _course_svc.update_chapter(
                chapter=chapter,
                title=form.cleaned_data["title"],
                content=form.cleaned_data["content"],
                order=form.cleaned_data.get("order", 0),
                new_image=new_image,
            )
            flash.success(request, f'Chapter "{chapter.title}" updated.')
            return redirect("admin_course_edit", course_id=chapter.course.id)
        except ValueError as exc:
            flash.error(request, str(exc))

    return render(request, "core/chapter_form.html", {
        "page_name": f"Edit Chapter — {chapter.title}",
        "form":      form,
        "chapter":   chapter,
        "course":    chapter.course,
        "action":    "Save Changes",
        "user":      request.user,
    })


@role_required("admin")
@require_POST
def admin_chapter_delete(request, chapter_id: int):
    """Delete a chapter and redirect back to its parent course edit page."""
    chapter   = get_object_or_404(Chapter, pk=chapter_id)
    course_id = _course_svc.delete_chapter(chapter)
    flash.success(request, "Chapter deleted.")
    return redirect("admin_course_edit", course_id=course_id)
