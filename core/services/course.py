"""
core/services/course.py
───────────────────────
CourseService: business logic for course and chapter administration.

Responsibilities
----------------
- Creating and updating courses (with creator attribution and price).
- Creating and updating chapters (with automatic image captioning).
- Deleting courses and chapters safely.

Design notes
------------
- Image captioning is injected via a callable (captioner) to make the service
  unit-testable without a real ML model (Dependency Inversion).
- Default captioner is the production utility; tests can pass a stub.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Callable

from ..models import Chapter, Course
from ..utils import generate_image_caption

if TYPE_CHECKING:
    from ..models import User


# Type alias for the captioning callable
ImageCaptioner = Callable[[str], str]


class CourseService:
    """Encapsulates course and chapter CRUD business logic."""

    def __init__(self, captioner: ImageCaptioner = generate_image_caption) -> None:
        """
        Parameters
        ----------
        captioner:
            A callable that accepts a filesystem path (str) and returns a text
            description of the image. Defaults to the production AI captioner.
        """
        self._captioner = captioner

    # ── Course operations ─────────────────────────────────────────────────────

    @staticmethod
    def create_course(
        title: str,
        description: str,
        created_by: "User",
        price: Decimal = Decimal("0.00"),
    ) -> Course:
        """
        Persist and return a new Course.

        Parameters
        ----------
        title       : Course title (required, non-blank).
        description : Optional description text.
        created_by  : The admin User creating the course.
        price       : Decimal price; 0.00 means free (default).

        Raises ValueError if title is blank or price is negative.
        """
        title = title.strip()
        if not title:
            raise ValueError("Course title cannot be empty.")

        try:
            price = Decimal(str(price))
        except Exception:
            raise ValueError("Invalid price value.")

        if price < 0:
            raise ValueError("Course price cannot be negative.")

        return Course.objects.create(
            title=title,
            description=description.strip(),
            price=price,
            created_by=created_by,
        )

    @staticmethod
    def update_course(
        course: Course,
        title: str,
        description: str,
        price: Decimal = None,
    ) -> Course:
        """
        Update and save a Course's mutable fields.

        If *price* is None, the existing price is left unchanged.
        """
        title = title.strip()
        if not title:
            raise ValueError("Course title cannot be empty.")

        course.title       = title
        course.description = description.strip()

        if price is not None:
            try:
                price = Decimal(str(price))
            except Exception:
                raise ValueError("Invalid price value.")
            if price < 0:
                raise ValueError("Course price cannot be negative.")
            course.price = price

        course.save(update_fields=["title", "description", "price", "updated_at"])
        return course

    @staticmethod
    def delete_course(course: Course) -> str:
        """Delete *course* and return its title (for confirmation messages)."""
        title = course.title
        course.delete()
        return title

    # ── Chapter operations ────────────────────────────────────────────────────

    def create_chapter(
        self,
        course: Course,
        title: str,
        content: str,
        order: int = 0,
        image=None,
    ) -> Chapter:
        """
        Persist a new Chapter, auto-generating an image description when an
        image is provided.
        """
        title, content = title.strip(), content.strip()
        if not title:
            raise ValueError("Chapter title cannot be empty.")
        if not content:
            raise ValueError("Chapter content cannot be empty.")

        chapter = Chapter.objects.create(
            course=course,
            title=title,
            content=content,
            order=order,
            image=image,
        )

        if image:
            chapter.image_description = self._captioner(chapter.image.path)
            chapter.save(update_fields=["image_description"])

        return chapter

    def update_chapter(
        self,
        chapter: Chapter,
        title: str,
        content: str,
        order: int,
        new_image=None,
    ) -> Chapter:
        """
        Update a chapter's fields. If *new_image* is provided the old image
        is replaced and a fresh AI caption is generated.
        """
        title, content = title.strip(), content.strip()
        if not title:
            raise ValueError("Chapter title cannot be empty.")
        if not content:
            raise ValueError("Chapter content cannot be empty.")

        chapter.title   = title
        chapter.content = content
        chapter.order   = order

        if new_image:
            chapter.image = new_image
            chapter.save()
            chapter.image_description = self._captioner(chapter.image.path)
            chapter.save(update_fields=["image_description"])
        else:
            chapter.save(update_fields=["title", "content", "order", "updated_at"])

        return chapter

    @staticmethod
    def delete_chapter(chapter: Chapter) -> int:
        """Delete *chapter* and return its parent course's PK."""
        course_id = chapter.course.id
        chapter.delete()
        return course_id
