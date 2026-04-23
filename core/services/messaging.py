"""
core/services/messaging.py
──────────────────────────
MessageService: all business logic for the learner ↔ mentor chat system.

Responsibilities
----------------
- Fetching the full conversation thread between two users.
- Sending a validated message after authorization checks.
- Enforcing the communication policy:
    Learner → only their assigned mentor.
    Mentor  → only their assigned learners.
- Marking received messages as read.

Design notes
------------
- Raises PermissionError for authorization failures so callers (views / API
  handlers) can translate them into the appropriate HTTP responses.
- Raises ValueError for empty-content messages.
- No HTTP objects cross this boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet

from ..models import Message, MentorAssignment

if TYPE_CHECKING:
    from ..models import User


class MessageService:
    """Encapsulates chat business logic and authorization rules."""

    # ── Queries ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_thread(user_a: "User", user_b: "User") -> QuerySet:
        """
        Return the ordered queryset of messages exchanged between two users.
        Messages sent by *user_a* to *user_b* receive is_read=True updates.
        """
        thread = Message.objects.filter(
            Q(sender=user_a, receiver=user_b) |
            Q(sender=user_b, receiver=user_a)
        ).order_by("timestamp")

        # Mark incoming as read
        thread.filter(receiver=user_a, is_read=False).update(is_read=True)
        return thread

    # ── Authorization ─────────────────────────────────────────────────────────

    @staticmethod
    def assert_may_message(sender: "User", receiver: "User") -> None:
        """
        Raise PermissionError if the platform's communication policy prevents
        *sender* from messaging *receiver*.

        Policy:
          - Learner may only message their assigned mentor.
          - Mentor may only message learners assigned to them.
          - Admin accounts do not participate in chat.
        """
        if sender.role == "learner":
            try:
                allowed_mentor = sender.mentor_assignment.mentor
            except MentorAssignment.DoesNotExist:
                raise PermissionError("You do not have a mentor assigned yet.")
            if not allowed_mentor or receiver.id != allowed_mentor.id:
                raise PermissionError("You may only message your assigned mentor.")

        elif sender.role == "mentor":
            is_assigned = MentorAssignment.objects.filter(
                mentor=sender, learner=receiver
            ).exists()
            if not is_assigned:
                raise PermissionError("You may only message learners assigned to you.")

        else:
            raise PermissionError("Admin accounts cannot participate in chat.")

    # ── Mutations ─────────────────────────────────────────────────────────────

    @classmethod
    def send_message(cls, sender: "User", receiver: "User", content: str) -> Message:
        """
        Validate, authorize, persist, and return a new Message.

        Raises
        ------
        ValueError       – content is blank.
        PermissionError  – sender is not allowed to message receiver.
        """
        content = content.strip()
        if not content:
            raise ValueError("Message content cannot be empty.")

        cls.assert_may_message(sender, receiver)

        return Message.objects.create(
            sender=sender,
            receiver=receiver,
            content=content,
        )

    # ── Mentor helpers ────────────────────────────────────────────────────────

    @staticmethod
    def get_assigned_mentor(learner: "User") -> "User | None":
        """Return the mentor assigned to *learner*, or None."""
        try:
            return learner.mentor_assignment.mentor
        except MentorAssignment.DoesNotExist:
            return None

    @staticmethod
    def assert_learner_assigned_to_mentor(mentor: "User", learner: "User") -> None:
        """Raise PermissionError if *learner* is not assigned to *mentor*."""
        is_assigned = MentorAssignment.objects.filter(
            mentor=mentor, learner=learner
        ).exists()
        if not is_assigned:
            raise PermissionError("This learner is not assigned to you.")
