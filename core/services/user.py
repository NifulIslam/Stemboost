"""
core/services/user.py
─────────────────────
UserService: business logic for user and mentor-assignment management.

Responsibilities
----------------
- Safe user deletion (enforces admin-protection and self-deletion rules).
- Assigning (and re-assigning) a mentor to a learner.
- Building the annotated learner list shown on the admin dashboard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import MentorAssignment, User

if TYPE_CHECKING:
    pass


class UserService:
    """Encapsulates user-management and mentor-assignment logic."""

    # ── Deletion ──────────────────────────────────────────────────────────────

    @staticmethod
    def delete_user(actor: User, target: User) -> str:
        """
        Delete *target* on behalf of *actor* (an admin).

        Returns the deleted user's email for confirmation messages.

        Raises
        ------
        PermissionError – if the deletion is not allowed by platform rules.
        """
        if target.id == actor.id:
            raise PermissionError("You cannot delete your own account.")
        if target.role == User.ROLE_ADMIN:
            raise PermissionError("Admin accounts cannot be deleted by other admins.")

        email = target.email
        target.delete()
        return email

    # ── Mentor assignment ─────────────────────────────────────────────────────

    @staticmethod
    def assign_mentor(learner: User, mentor: User, assigned_by: User) -> MentorAssignment:
        """
        Create or update the MentorAssignment for *learner*.

        Raises
        ------
        ValueError – if *learner* is not a learner or *mentor* is not a mentor.
        """
        if learner.role != User.ROLE_LEARNER:
            raise ValueError(f"User {learner.email!r} is not a learner.")
        if mentor.role != User.ROLE_MENTOR:
            raise ValueError(f"User {mentor.email!r} is not a mentor.")

        assignment, _ = MentorAssignment.objects.update_or_create(
            learner=learner,
            defaults={"mentor": mentor, "assigned_by": assigned_by},
        )
        return assignment

    # ── Dashboard helpers ─────────────────────────────────────────────────────

    @staticmethod
    def get_assigned_mentor(learner: User) -> "User | None":
        """Return the mentor currently assigned to *learner*, or None."""
        try:
            return learner.mentor_assignment.mentor
        except MentorAssignment.DoesNotExist:
            return None

    @staticmethod
    def build_learner_rows(learners) -> list[dict]:
        """
        For each learner queryset row, attach their currently assigned mentor.
        Returns a list of {'user': User, 'mentor': User | None} dicts.
        """
        rows = []
        for learner in learners:
            rows.append({
                "user":   learner,
                "mentor": UserService.get_assigned_mentor(learner),
            })
        return rows

    @staticmethod
    def get_assigned_learners(mentor: User) -> list[User]:
        """Return the list of learners currently assigned to *mentor*."""
        assignments = (
            MentorAssignment.objects
            .filter(mentor=mentor)
            .select_related("learner")
        )
        return [a.learner for a in assignments]
