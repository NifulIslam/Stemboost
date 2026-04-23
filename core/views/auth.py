"""
core/views/auth.py
──────────────────
Authentication views: landing, login, register, logout.

Each view has a single responsibility (SRP):
- No business logic lives here; only form handling and HTTP concerns.
- Delegates role-based redirect to the User model's get_dashboard_url().
"""

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from ..forms import LoginForm, RegisterForm


def landing(request):
    """Public landing page. Authenticated users are forwarded to their dashboard."""
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())
    return render(request, "core/landing.html")


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Email + password login. Valid sessions redirect by role."""
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    form          = LoginForm(request.POST or None)
    error_message = None

    if request.method == "POST" and form.is_valid():
        email    = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        user     = authenticate(request, username=email, password=password)

        if user is None:
            error_message = "Invalid email address or password. Please try again."
        elif not user.is_active:
            error_message = "Your account has been disabled. Please contact support."
        else:
            login(request, user)
            return redirect(user.get_dashboard_url())

    return render(request, "core/login.html", {
        "form":          form,
        "error_message": error_message,
        "page_name":     "Login Page",
    })


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Self-service registration. Logs the user in on success."""
    if request.user.is_authenticated:
        return redirect(request.user.get_dashboard_url())

    form = RegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(user.get_dashboard_url())

    return render(request, "core/register.html", {
        "form":      form,
        "page_name": "Registration Page",
    })


def logout_view(request):
    """Log out and redirect to landing page."""
    logout(request)
    return redirect("/")
