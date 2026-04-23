"""
core/views/commerce.py
───────────────────────
Commerce views for STEMboost: cart, enrollment, and demo transactions.

All views are restricted to learner role via @role_required.
No real payment processing occurs; this is a simulated demo flow.
"""

import logging

from django.contrib import messages as flash
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import Course, Transaction
from ..services import CommerceService
from .decorators import role_required

logger = logging.getLogger(__name__)


# ── Cart ──────────────────────────────────────────────────────────────────────

@role_required("learner")
def cart_view(request):
    """Show the learner's shopping cart."""
    learner = request.user
    items   = CommerceService.get_cart_items(learner)
    total   = CommerceService.cart_total(items)
    paid_count = sum(1 for i in items if i.course.price > 0)
    free_count = sum(1 for i in items if i.course.price == 0)

    return render(request, "core/cart.html", {
        "page_name":  "Shopping Cart",
        "user":       learner,
        "cart_items": items,
        "cart_total": total,
        "paid_count": paid_count,
        "free_count": free_count,
    })


@role_required("learner")
@require_POST
def cart_add(request, course_id: int):
    """Add a course to the learner's cart."""
    course  = get_object_or_404(Course, pk=course_id)
    learner = request.user

    try:
        CommerceService.add_to_cart(learner, course)
        flash.success(request, f'"{course.title}" has been added to your cart.')
    except ValueError as exc:
        flash.error(request, str(exc))

    # Always return to the dashboard so the learner can keep browsing
    return redirect("learner_dashboard")


@role_required("learner")
@require_POST
def cart_remove(request, course_id: int):
    """Remove a course from the learner's cart."""
    course  = get_object_or_404(Course, pk=course_id)
    learner = request.user

    CommerceService.remove_from_cart(learner, course)
    flash.success(request, f'"{course.title}" removed from your cart.')
    return redirect("cart_view")


# ── Direct Enrollment (free courses) ─────────────────────────────────────────

@role_required("learner")
@require_POST
def enroll_free(request, course_id: int):
    """
    Enroll the learner directly in a free course (no payment required).
    Redirects to the learner dashboard on success.
    """
    course  = get_object_or_404(Course, pk=course_id)
    learner = request.user

    try:
        CommerceService.enroll_free_course(learner, course)
        flash.success(
            request,
            f'You are now enrolled in "{course.title}". Happy learning!'
        )
    except ValueError as exc:
        flash.error(request, str(exc))

    return redirect("learner_dashboard")


# ── Checkout: buy a single paid course ───────────────────────────────────────

@role_required("learner")
def checkout_single(request, course_id: int):
    """
    Initiate a demo purchase for a single paid course.
    GET: show the demo payment page.
    POST: process the demo transaction (pay / cancel / fail).
    """
    course  = get_object_or_404(Course, pk=course_id)
    learner = request.user

    # Guard: free courses shouldn't reach here
    if course.price <= 0:
        flash.error(request, "This course is free — use the Enroll button instead.")
        return redirect("learner_dashboard")

    # Guard: already enrolled
    if CommerceService.is_enrolled(learner, course):
        flash.success(request, f'You are already enrolled in "{course.title}".')
        return redirect("learner_dashboard")

    if request.method == "POST":
        return _process_single_checkout(request, learner, course)

    # Create a pending transaction so the ref exists before the page renders
    try:
        tx = CommerceService.create_transaction(learner, [course])
    except ValueError as exc:
        flash.error(request, str(exc))
        return redirect("learner_dashboard")

    return render(request, "core/checkout.html", {
        "page_name":   f"Purchase: {course.title}",
        "user":        learner,
        "transaction": tx,
        "courses":     [course],
        "total":       tx.amount,
    })


def _process_single_checkout(request, learner, course):
    """Handle POST from a single-course checkout page."""
    tx_ref = request.POST.get("transaction_ref", "").strip()
    action = request.POST.get("action", "").strip()

    try:
        tx = Transaction.objects.get(
            transaction_ref=tx_ref, learner=learner, status=Transaction.STATUS_PENDING
        )
    except Transaction.DoesNotExist:
        flash.error(request, "Transaction not found or already processed.")
        return redirect("learner_dashboard")

    try:
        CommerceService.process_transaction(tx, action)
    except ValueError as exc:
        flash.error(request, str(exc))
        return redirect("learner_dashboard")

    return redirect("transaction_result", tx_ref=tx.transaction_ref)


# ── Checkout: buy from cart ───────────────────────────────────────────────────

@role_required("learner")
def checkout_cart(request):
    """
    Initiate a demo purchase for all items in the learner's cart.
    GET: show the demo payment page.
    POST: process the demo transaction.
    """
    learner = request.user
    items   = CommerceService.get_cart_items(learner)

    if not items:
        flash.error(request, "Your cart is empty.")
        return redirect("cart_view")

    # Separate free from paid
    paid_items = [item for item in items if item.course.price > 0]
    free_items = [item for item in items if item.course.price == 0]

    if request.method == "POST":
        return _process_cart_checkout(request, learner, paid_items, free_items)

    if not paid_items:
        # All items are free — enroll all directly
        for item in free_items:
            try:
                CommerceService.enroll(learner, item.course)
            except Exception:
                pass
        CommerceService.clear_cart(learner)
        flash.success(request, "You have been enrolled in all free courses.")
        return redirect("learner_dashboard")

    # Create pending transaction for paid items only
    try:
        tx = CommerceService.create_transaction(learner, [i.course for i in paid_items])
    except ValueError as exc:
        flash.error(request, str(exc))
        return redirect("cart_view")

    return render(request, "core/checkout.html", {
        "page_name":   "Cart Checkout",
        "user":        learner,
        "transaction": tx,
        "courses":     [i.course for i in paid_items],
        "free_courses": [i.course for i in free_items],
        "total":       tx.amount,
    })


def _process_cart_checkout(request, learner, paid_items, free_items):
    """Handle POST from the cart checkout page."""
    tx_ref = request.POST.get("transaction_ref", "").strip()
    action = request.POST.get("action", "").strip()

    try:
        tx = Transaction.objects.get(
            transaction_ref=tx_ref, learner=learner, status=Transaction.STATUS_PENDING
        )
    except Transaction.DoesNotExist:
        flash.error(request, "Transaction not found or already processed.")
        return redirect("cart_view")

    try:
        CommerceService.process_transaction(tx, action)
    except ValueError as exc:
        flash.error(request, str(exc))
        return redirect("cart_view")

    # On success also enroll in free items and clear them
    if tx.status == Transaction.STATUS_SUCCESS and free_items:
        for item in free_items:
            try:
                CommerceService.enroll(learner, item.course)
            except Exception:
                pass
        for item in free_items:
            CommerceService.remove_from_cart(learner, item.course)

    return redirect("transaction_result", tx_ref=tx.transaction_ref)


# ── Transaction Result ────────────────────────────────────────────────────────

@role_required("learner")
def transaction_result(request, tx_ref: str):
    """Show the result of a completed demo transaction."""
    learner = request.user
    tx      = get_object_or_404(Transaction, transaction_ref=tx_ref, learner=learner)
    courses = tx.courses.all()

    return render(request, "core/transaction_result.html", {
        "page_name":   "Transaction Result",
        "user":        learner,
        "transaction": tx,
        "courses":     courses,
    })
