"""
core/views/decorators.py
────────────────────────
Shared view decorators for STEMboost.

role_required(role)
    Decorator factory that restricts a view to users with the given role.
    Unauthenticated users are redirected to the login page.
    Authenticated users with the wrong role are redirected to their own dashboard.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(role: str):
    """
    Decorator factory: ensures the logged-in user has the given role string.

    Usage::

        @role_required('learner')
        def my_view(request):
            ...

    Design: Open/Closed — new roles are handled without modifying this function.
    """
    def decorator(view_func):
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                return redirect(request.user.get_dashboard_url())
            return view_func(request, *args, **kwargs)

        # Preserve the original function's name and docstring
        wrapped.__name__    = view_func.__name__
        wrapped.__doc__     = view_func.__doc__
        wrapped.__module__  = view_func.__module__
        return wrapped

    return decorator
