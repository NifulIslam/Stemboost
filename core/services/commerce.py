"""
core/services/commerce.py
──────────────────────────
CommerceService: business logic for cart, enrollment, and demo transactions.

Responsibilities
----------------
- Cart management (add, remove, list, clear).
- Direct enrollment for free courses.
- Creating and processing demo transactions for paid courses.
- Enrolling learners after successful payment.

Design notes
------------
- All methods are class-level; no instance state needed.
- Raises ValueError for invalid operations (duplicate, wrong role, etc.).
- Transaction references are generated with uuid4 for uniqueness and safety.
- No real payment gateway calls are made; this is a simulation.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from ..models import CartItem, Course, Enrollment, Transaction

if TYPE_CHECKING:
    from ..models import User


class CommerceService:
    """Encapsulates cart, enrollment, and demo-transaction business logic."""

    # ── Cart ──────────────────────────────────────────────────────────────────

    @staticmethod
    def get_cart_items(learner: "User") -> list[CartItem]:
        """Return all cart items for *learner*, newest first."""
        return list(
            CartItem.objects.filter(learner=learner).select_related("course")
        )

    @staticmethod
    def get_cart_count(learner: "User") -> int:
        """Return the number of items currently in the learner's cart."""
        return CartItem.objects.filter(learner=learner).count()

    @staticmethod
    def cart_total(items: list[CartItem]) -> Decimal:
        """Return the sum of prices of all *items*."""
        return sum(item.course.price for item in items)

    @staticmethod
    def add_to_cart(learner: "User", course: Course) -> CartItem:
        """
        Add *course* to *learner*'s cart.

        Raises ValueError if:
        - The learner is already enrolled in the course.
        - The course is already in the cart.
        """
        if Enrollment.objects.filter(learner=learner, course=course).exists():
            raise ValueError(f'You are already enrolled in "{course.title}".')

        item, created = CartItem.objects.get_or_create(learner=learner, course=course)
        if not created:
            raise ValueError(f'"{course.title}" is already in your cart.')
        return item

    @staticmethod
    def remove_from_cart(learner: "User", course: Course) -> None:
        """Remove *course* from *learner*'s cart (silent if not present)."""
        CartItem.objects.filter(learner=learner, course=course).delete()

    @staticmethod
    def clear_cart(learner: "User") -> None:
        """Remove all items from *learner*'s cart."""
        CartItem.objects.filter(learner=learner).delete()

    # ── Enrollment ────────────────────────────────────────────────────────────

    @staticmethod
    def enroll(learner: "User", course: Course) -> Enrollment:
        """
        Enroll *learner* in *course* (idempotent).
        Returns the Enrollment, whether new or existing.
        """
        enrollment, _ = Enrollment.objects.get_or_create(
            learner=learner, course=course
        )
        return enrollment

    @staticmethod
    def is_enrolled(learner: "User", course: Course) -> bool:
        """Return True if *learner* is already enrolled in *course*."""
        return Enrollment.objects.filter(learner=learner, course=course).exists()

    @staticmethod
    def get_enrolled_course_ids(learner: "User") -> set[int]:
        """Return the set of course PKs the learner is enrolled in."""
        return set(
            Enrollment.objects.filter(learner=learner)
            .values_list("course_id", flat=True)
        )

    @classmethod
    def enroll_free_course(cls, learner: "User", course: Course) -> Enrollment:
        """
        Enroll a learner in a free course directly (no payment required).

        Raises ValueError if the course is not free or already enrolled.
        """
        if course.price > 0:
            raise ValueError(
                f'"{course.title}" is a paid course. Please purchase it first.'
            )
        if cls.is_enrolled(learner, course):
            raise ValueError(f'You are already enrolled in "{course.title}".')
        return cls.enroll(learner, course)

    # ── Demo Transactions ─────────────────────────────────────────────────────

    @staticmethod
    def _generate_ref() -> str:
        """Generate a unique transaction reference string."""
        return f"DEMO-{uuid.uuid4().hex[:16].upper()}"

    @classmethod
    def create_transaction(
        cls,
        learner: "User",
        courses: list[Course],
    ) -> Transaction:
        """
        Create a PENDING demo transaction for the given list of courses.

        Raises ValueError if any course is free or already enrolled.
        """
        if not courses:
            raise ValueError("No courses selected for purchase.")

        for course in courses:
            if course.price <= 0:
                raise ValueError(
                    f'"{course.title}" is free — use direct enrollment instead.'
                )
            if Enrollment.objects.filter(learner=learner, course=course).exists():
                raise ValueError(f'You are already enrolled in "{course.title}".')

        total = sum(c.price for c in courses)
        ref   = cls._generate_ref()

        tx = Transaction.objects.create(
            learner=learner,
            amount=total,
            status=Transaction.STATUS_PENDING,
            transaction_ref=ref,
        )
        tx.courses.set(courses)
        return tx

    @classmethod
    def process_transaction(
        cls,
        transaction: Transaction,
        action: str,          # 'pay' | 'cancel' | 'fail'
    ) -> Transaction:
        """
        Process a demo transaction.

        - action='pay'    → mark SUCCESS, create Enrollments, clear cart items
        - action='cancel' → mark CANCELLED
        - action='fail'   → mark FAILED

        Returns the updated Transaction.
        Raises ValueError if transaction is not in PENDING state.
        """
        if transaction.status != Transaction.STATUS_PENDING:
            raise ValueError(
                f"Transaction {transaction.transaction_ref} is already {transaction.status}."
            )

        if action == "pay":
            transaction.status = Transaction.STATUS_SUCCESS
            transaction.save(update_fields=["status", "updated_at"])

            # Enroll learner in all purchased courses
            for course in transaction.courses.all():
                cls.enroll(transaction.learner, course)
                # Remove from cart if it was added
                CartItem.objects.filter(
                    learner=transaction.learner, course=course
                ).delete()

        elif action == "cancel":
            transaction.status = Transaction.STATUS_CANCELLED
            transaction.save(update_fields=["status", "updated_at"])

        elif action == "fail":
            transaction.status = Transaction.STATUS_FAILED
            transaction.save(update_fields=["status", "updated_at"])

        else:
            raise ValueError(f"Unknown action: {action!r}")

        return transaction
