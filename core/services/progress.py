"""
core/services/progress.py
─────────────────────────
ProgressService: all business logic related to learner progress tracking.

Responsibilities
----------------
- Computing per-course progress percentages for a given learner.
- Assembling the full course-progress snapshot used by the learner dashboard
  and the mentor's per-learner progress view.
- Marking a chapter as completed and returning updated progress.

Design notes
------------
- Pure service class (no Django view concerns, no HTTP objects).
- All methods are static/classmethod: the class acts as a namespace.
- Raises ValueError on bad inputs so callers can handle them explicitly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet

from ..models import Chapter, ChapterCompletion, Course

if TYPE_CHECKING:
    from ..models import User


class ProgressService:
    """Encapsulates all learner-progress business logic."""

    # ── Core computation ──────────────────────────────────────────────────────

    @staticmethod
    def compute_course_progress(learner: "User", course: Course) -> int:
        """
        Return an integer 0-100 representing how many chapters the learner
        has completed in *course*. Returns 0 if the course has no chapters.
        """
        total = course.chapters.count()
        if total == 0:
            return 0
        done = ChapterCompletion.objects.filter(
            learner=learner,
            chapter__course=course,
        ).count()
        return round((done / total) * 100)

    @staticmethod
    def get_completed_chapter_ids(learner: "User") -> set:
        """Return the set of chapter PKs the learner has completed (all courses)."""
        return set(
            ChapterCompletion.objects.filter(learner=learner)
            .values_list("chapter_id", flat=True)
        )

    # ── Dashboard snapshots ───────────────────────────────────────────────────

    @classmethod
    def build_courses_snapshot(
        cls,
        learner: "User",
        courses_qs: QuerySet,
    ) -> list:
        """
        For each course in *courses_qs*, return a dict containing:
          id, title, description, chapter_count, progress (0-100),
          and a list of chapter dicts (id, title, is_completed).

        Uses a single pre-fetched set of completed IDs to avoid N+1 queries.
        """
        completed_ids = cls.get_completed_chapter_ids(learner)
        snapshot = []

        for course in courses_qs:
            chapters = list(course.chapters.order_by("order", "id"))
            total    = len(chapters)
            done     = sum(1 for ch in chapters if ch.id in completed_ids)
            progress = round((done / total) * 100) if total else 0

            snapshot.append({
                "id":            course.id,
                "title":         course.title,
                "description":   course.description,
                "chapter_count": total,
                "progress":      progress,
                "chapters": [
                    {
                        "id":           ch.id,
                        "title":        ch.title,
                        "is_completed": ch.id in completed_ids,
                    }
                    for ch in chapters
                ],
            })

        return snapshot

    @classmethod
    def build_enrolled_courses_snapshot(cls, learner: "User") -> list:
        """
        Build the course snapshot restricted to courses the learner is enrolled in.
        Used by the learner dashboard to show only enrolled/accessible courses.
        """
        from ..models import Enrollment
        enrolled_ids = Enrollment.objects.filter(learner=learner).values_list(
            "course_id", flat=True
        )
        courses_qs = Course.objects.filter(
            id__in=enrolled_ids
        ).prefetch_related("chapters")
        return cls.build_courses_snapshot(learner, courses_qs)

    @classmethod
    def build_learner_progress_for_mentor(cls, learner: "User") -> list:
        """
        Build the full progress snapshot for *learner* across every course,
        intended for display on the mentor's learner-progress page.

        Shows all courses (not just enrolled), so the mentor sees the complete
        picture of what the learner has and hasn't started.
        """
        courses_qs = Course.objects.prefetch_related("chapters")
        return cls.build_courses_snapshot(learner, courses_qs)

    # ── Summary statistics ────────────────────────────────────────────────────

    @staticmethod
    def compute_overall_stats(courses_snapshot: list) -> dict:
        """
        Given the list returned by build_courses_snapshot, return a dict with:
          total_courses, completed_count, overall_progress (0-100 average).
        """
        total     = len(courses_snapshot)
        completed = sum(1 for c in courses_snapshot if c["progress"] == 100)
        average   = (
            round(sum(c["progress"] for c in courses_snapshot) / total)
            if total else 0
        )
        return {
            "total_courses":    total,
            "completed_count":  completed,
            "overall_progress": average,
        }

    # ── Chapter completion mutation ───────────────────────────────────────────

    @classmethod
    def mark_chapter_complete(cls, learner: "User", chapter: Chapter) -> int:
        """
        Record that *learner* has completed *chapter* (idempotent).
        Returns the updated course progress percentage (0-100).
        """
        ChapterCompletion.objects.get_or_create(learner=learner, chapter=chapter)
        return cls.compute_course_progress(learner, chapter.course)
