# STEMboost

**An accessible STEM learning platform for blind and visually-impaired (BVI) learners.**

STEMboost connects learners with mentors through structured, audio-first courses. Admins manage courses and assignments; mentors track learner progress and chat directly with their assigned students; learners read chapters aloud using built-in text-to-speech.

---

## Table of Contents

1. [Features](#features)
2. [User Roles & Workflows](#user-roles--workflows)
3. [Technology Stack](#technology-stack)
4. [Folder Structure](#folder-structure)
5. [Installation & Setup](#installation--setup)
6. [Running the Application](#running-the-application)
7. [Migrations](#migrations)
8. [Environment & Configuration](#environment--configuration)
9. [Testing](#testing)
10. [Assumptions](#assumptions)

---

## Features

### Admin
- **User management** — view all users; delete learner and mentor accounts (admins are protected from deletion).
- **Course management** — create, edit, and delete courses. Each course contains ordered chapters.
- **Chapter management** — each chapter has a title, rich text content, and an optional image. On upload, an AI model automatically generates an image description (metadata) stored alongside the chapter.
- **Mentor assignment** — assign or re-assign a mentor to any learner from a dropdown. Re-assignment updates the existing record safely.

### Mentor
- **Assigned-learner view** — see only the learners assigned to you (not platform-wide).
- **Per-learner course progress** — click "View Progress" on any assigned learner to see a full course-by-course breakdown: overall progress percentage, progress bar, and per-chapter ✅/○ completion status.
- **Direct chat** — real-time chat (2-second polling) with each assigned learner. Messages persist in the database.

### Learner
- **Course catalogue** — all admin-created courses appear on the dashboard with progress bars and chapter lists.
- **Course search** — filter courses by title or description using the search bar.
- **Chapter reading** — click any chapter to open the reader. Press "Read Aloud" (or `Ctrl+R`) to trigger the browser's Web Speech API, which reads the chapter text and then the AI-generated image description aloud.
- **Progress tracking** — clicking "Mark as Complete" on a chapter records a `ChapterCompletion` entry; the course progress bar updates immediately via AJAX.
- **Mentor status** — if no mentor is assigned, a clear message instructs the learner to wait. Once assigned, a chat link appears.
- **Direct chat** — real-time chat with the assigned mentor. Only the assigned mentor may be messaged.

### Security
- Role-based access control on every view — wrong-role users are redirected to their own dashboard.
- Admins cannot delete other admin accounts.
- Chat messages are strictly scoped: learners → their assigned mentor; mentors → their assigned learners.
- CSRF tokens on every state-changing form and AJAX POST.

---

## User Roles & Workflows

```
┌─────────────┐     assigns mentor     ┌──────────────┐
│    Admin    │──────────────────────▶ │   Learner    │
│             │                        │              │
│ • CRUD      │     creates courses    │ • reads      │
│   courses   │──────────────────────▶ │   chapters   │
│ • CRUD      │                        │ • marks      │
│   chapters  │                        │   complete   │
│ • manage    │                        │ • chats with │
│   users     │                        │   mentor     │
└─────────────┘                        └──────┬───────┘
                                              │ assigned to
                                        ┌─────▼───────┐
                                        │   Mentor    │
                                        │             │
                                        │ • views     │
                                        │   learner   │
                                        │   progress  │
                                        │ • chats     │
                                        └─────────────┘
```

**Typical admin workflow:**
1. Log in → Admin Dashboard.
2. Create a course → add chapters with text + optional image.
3. Assign each learner a mentor.

**Typical learner workflow:**
1. Register as "Learner" → Learner Dashboard.
2. Browse / search courses.
3. Click a chapter → press Read Aloud → press Mark as Complete.
4. Chat with the assigned mentor.

**Typical mentor workflow:**
1. Log in → Mentor Dashboard.
2. See list of assigned learners.
3. Click "View Progress" to review a learner's course completion.
4. Click "Chat" to message that learner.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.x |
| Database | SQLite (dev) — swap for PostgreSQL in production |
| Auth | Django's AbstractBaseUser + custom email-based login |
| Static files | WhiteNoise |
| Media files | Django's `MEDIA_ROOT` + `static()` dev-server route |
| Text-to-speech | Browser Web Speech API (`SpeechSynthesis`) |
| Image captioning | `microsoft/git-base-coco` via HuggingFace `transformers` |
| Styling | Custom CSS (dark theme, CSS variables, WCAG AAA contrast) |

---

## Folder Structure

```
stemboost/                      ← Django project root
├── manage.py
├── requirements.txt
├── stemboost/                  ← Project settings package
│   ├── settings.py
│   ├── urls.py                 ← Root URL config (includes core + media)
│   └── wsgi.py
└── core/                       ← Main application
    ├── models.py               ← All database models
    ├── forms.py                ← Django forms (Login, Register, Course, Chapter)
    ├── urls.py                 ← All URL patterns
    ├── utils.py                ← Image captioning utility
    ├── admin.py                ← Django admin registrations
    ├── apps.py
    │
    ├── services/               ← Business logic layer
    │   ├── __init__.py
    │   ├── progress.py         ← ProgressService
    │   ├── messaging.py        ← MessageService
    │   ├── course.py           ← CourseService
    │   └── user.py             ← UserService
    │
    ├── views/                  ← HTTP layer (thin; delegates to services)
    │   ├── __init__.py         ← Re-exports all views for urls.py
    │   ├── decorators.py       ← role_required decorator
    │   ├── auth.py             ← landing, login, register, logout
    │   ├── learner.py          ← Learner dashboard, chapter view, chat
    │   ├── mentor.py           ← Mentor dashboard, learner progress, chat
    │   ├── admin.py            ← Admin dashboard, CRUD views
    │   └── api.py              ← AJAX endpoints (messages, chapter complete)
    │
    ├── templates/core/
    │   ├── base.html
    │   ├── landing.html
    │   ├── login.html
    │   ├── register.html
    │   ├── dashboard_admin.html
    │   ├── dashboard_learner.html
    │   ├── dashboard_mentor.html
    │   ├── mentor_learner_progress.html  ← NEW: per-learner progress page
    │   ├── chapter_view.html
    │   ├── chat.html
    │   ├── course_form.html
    │   └── chapter_form.html
    │
    ├── static/core/
    │   ├── css/style.css
    │   └── js/audio.js
    │
    └── migrations/
        ├── 0001_initial.py     ← User model
        └── 0002_courses_and_features.py  ← All new models
```

---

## Installation & Setup

### Prerequisites

- Python 3.11+
- pip

### Steps

```bash
# 1. Unzip the project
unzip stemboost_integrated.zip
cd stemboost_output

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Optional: install AI image captioning support
#    (requires ~500 MB model download on first chapter image upload)
pip install transformers torch Pillow
```

`requirements.txt` minimum contents:

```
django>=5.0
whitenoise
pillow
```

---

## Migrations

```bash
# Apply all migrations (creates the SQLite database)
python manage.py migrate

# Create your first admin user
python manage.py createsuperuser
# enter: email, role (type 'admin'), password
```

Migration files:

| File | Creates |
|---|---|
| `0001_initial.py` | `User` model |
| `0002_courses_and_features.py` | `Course`, `Chapter`, `MentorAssignment`, `ChapterCompletion`, `Message` |

---

## Running the Application

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`.

**Collect static files** (before deploying or using WhiteNoise in production):

```bash
python manage.py collectstatic
```

---

## Environment & Configuration

All settings are in `stemboost/settings.py`. Key values to change for production:

| Setting | Development default | Production recommendation |
|---|---|---|
| `SECRET_KEY` | Hardcoded string | Load from environment variable |
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `['*']` | Your domain(s) |
| `DATABASES` | SQLite | PostgreSQL via `dj-database-url` |
| `STATICFILES_STORAGE` | WhiteNoise compressed | CDN / S3 |
| `MEDIA_ROOT` | `BASE_DIR/media` | Persistent volume / S3 |

---

## Testing

The service layer is designed for unit testing without requiring a running server or database. Example structure:

```python
# tests/test_progress.py
from unittest.mock import MagicMock
from core.services import ProgressService

def test_compute_progress_empty_course():
    learner = MagicMock()
    course  = MagicMock()
    course.chapters.count.return_value = 0
    assert ProgressService.compute_course_progress(learner, course) == 0

def test_course_service_uses_injected_captioner():
    from core.services.course import CourseService
    mock_captioner = MagicMock(return_value="a neural network diagram")
    svc = CourseService(captioner=mock_captioner)
    # ... test without loading the real ML model
```

Run tests:

```bash
python manage.py test core
```

---

## Assumptions

1. **Single mentor per learner** — the `MentorAssignment` model uses `OneToOneField` on the learner side. If the platform later requires multiple mentors, change to a `ManyToManyField`.
2. **No email verification** — registration is instant. Add `django-allauth` or similar for production email confirmation.
3. **AI captioning is optional** — if `transformers`/`torch` are not installed, `utils.generate_image_caption` falls back to a placeholder string. Chapters work normally; the description field is just empty.
4. **Chapter images served via Django dev server** — in production, serve `MEDIA_ROOT` via Nginx or an object store (S3/GCS).
5. **Chat polling interval is 2 seconds** — suitable for small user counts. For higher concurrency, replace with Django Channels (WebSockets).
6. **SQLite is for development only** — the schema is fully compatible with PostgreSQL; change `DATABASES` and install `psycopg2`.
7. **No password reset flow** — can be added with Django's built-in `PasswordResetView`.
