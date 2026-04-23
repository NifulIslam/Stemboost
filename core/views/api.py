"""
core/views/api.py
──────────────────
AJAX / JSON API endpoints consumed by the chat polling and chapter-complete
front-end scripts.

All endpoints require authentication.  Authorization is delegated to the
service layer which raises PermissionError on violations.

CSRF protection: Django's CsrfViewMiddleware is active for all POST requests.
The front-end JavaScript reads the csrftoken cookie and sends it in the
X-CSRFToken request header — the standard Django AJAX pattern.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..models import Message, User
from ..services import MessageService

logger = logging.getLogger(__name__)


# ── Message polling ───────────────────────────────────────────────────────────

@login_required
def api_messages(request, partner_id: int):
    """
    GET /api/messages/<partner_id>/

    Return the full conversation thread between the current user and
    *partner_id* as JSON, and mark incoming messages as read.

    Used by the 2-second polling loop in chat.html.
    """
    partner = get_object_or_404(User, pk=partner_id)
    me      = request.user

    thread = MessageService.get_thread(me, partner)
    payload = list(
        thread.values("id", "sender_id", "content", "timestamp", "is_read")
    )
    return JsonResponse({"messages": payload}, json_dumps_params={"default": str})


# ── Send message ──────────────────────────────────────────────────────────────

@require_POST
@login_required
def api_send_message(request):
    """
    POST /api/messages/send/

    Body (JSON): { "receiver_id": <int>, "content": "<str>" }

    Returns the persisted message as JSON, or an error object.
    Authorization rules are enforced by MessageService.send_message.
    """
    try:
        data     = json.loads(request.body)
        receiver = get_object_or_404(User, pk=int(data["receiver_id"]))
        content  = data.get("content", "")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    try:
        msg = MessageService.send_message(
            sender=request.user, receiver=receiver, content=content
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except PermissionError as exc:
        return JsonResponse({"error": str(exc)}, status=403)
    except Exception:
        logger.exception("Unexpected error in api_send_message")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)

    return JsonResponse({
        "id":        msg.id,
        "sender_id": msg.sender_id,
        "content":   msg.content,
        "timestamp": msg.timestamp.isoformat(),
    })
