# STEMboost — Architecture & Design Document

This document explains the technical decisions, design patterns, SOLID principles,
exception-handling strategy, CSRF protection, and the text-to-speech approach used
in the STEMboost platform.

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Design Patterns](#2-design-patterns)
3. [SOLID Principles](#3-solid-principles)
4. [Exception Handling](#4-exception-handling)
5. [CSRF Protection](#5-csrf-protection)
6. [Text-to-Speech: Method, Library & Rationale](#6-text-to-speech-method-library--rationale)
7. [Image Captioning Pipeline](#7-image-captioning-pipeline)
8. [Data Model Relationships](#8-data-model-relationships)
9. [Request Lifecycle](#9-request-lifecycle)

---

## 1. High-Level Architecture

STEMboost follows a **layered architecture** with three distinct layers inside the
Django application:

```
┌──────────────────────────────────────────────────────┐
│                    HTTP Layer                        │
│  core/views/  (auth, learner, mentor, admin, api)    │
│  • Handles request/response only                     │
│  • Form validation via Django Forms                  │
│  • No direct ORM queries — delegates to services     │
└────────────────────┬─────────────────────────────────┘
                     │ calls
┌────────────────────▼─────────────────────────────────┐
│                  Service Layer                       │
│  core/services/  (ProgressService, MessageService,   │
│                   CourseService, UserService)        │
│  • Pure business logic                               │
│  • No Django request/response objects                │
│  • Raises domain exceptions (ValueError, Permission) │
└────────────────────┬─────────────────────────────────┘
                     │ queries
┌────────────────────▼─────────────────────────────────┐
│                  Data Layer                          │
│  core/models.py  (User, Course, Chapter,             │
│                   MentorAssignment,                  │
│                   ChapterCompletion, Message)        │
│  • Django ORM models                                 │
│  • Manager methods and model properties              │
└──────────────────────────────────────────────────────┘
```

**Why three layers?**

- Views become thin and testable without a database (inject mock services).
- Services are testable without an HTTP client (unit tests call them directly).
- The model layer owns the schema; migrations are the only thing that changes it.

---

## 2. Design Patterns

### 2.1 Service Object Pattern

**Where:** `core/services/progress.py`, `messaging.py`, `course.py`, `user.py`

**What:** Each service class groups a cohesive set of operations on a domain
concept. They are stateless (static or instance methods with no shared mutable
state), making them trivially thread-safe.

```python
# Before refactor — business logic scattered in a view function:
def mentor_dashboard(request):
    assignments = MentorAssignment.objects.filter(mentor=mentor)
    learners    = [a.learner for a in assignments]
    ...

# After refactor — delegated to a focused service:
def mentor_dashboard(request):
    learners = UserService.get_assigned_learners(request.user)
    ...
```

The service layer forms a stable **API boundary**: views depend on service
method signatures, not on ORM internals. This means ORM queries can be
optimised (e.g. adding `select_related`) inside services without touching views.

---

### 2.2 Decorator Pattern

**Where:** `core/views/decorators.py` → `role_required`

**What:** `role_required` is a **decorator factory** — a function that returns
a decorator, which in turn wraps a view function. It adds authentication
and role-checking behaviour to any view without modifying the view itself.

```python
@role_required("mentor")
def mentor_dashboard(request):
    ...  # only reachable by mentors
```

This is the classic Decorator pattern: the original function's behaviour is
preserved and extended transparently. Django's own `@login_required` uses the
same mechanism; `role_required` composes on top of it.

The wrapped function's `__name__`, `__doc__`, and `__module__` are copied to
avoid breaking Django's URL reversal and admin introspection.

---

### 2.3 Dependency Injection (Constructor Injection)

**Where:** `core/services/course.py` → `CourseService.__init__`

**What:** `CourseService` accepts a `captioner` callable at construction time
rather than importing `generate_image_caption` directly. This makes the service
testable without loading a 500 MB ML model:

```python
# Production (default):
svc = CourseService()                         # uses real AI captioner

# In a unit test:
svc = CourseService(captioner=lambda p: "stub description")
```

The production view (`core/views/admin.py`) creates a single module-level
instance with the real captioner. Tests create their own instances with stubs.

This is **Dependency Inversion in practice**: `CourseService` depends on the
*abstraction* (any callable `str → str`) rather than the *concrete* captioner.

---

### 2.4 Template Method (via Django Forms)

**Where:** All form views in `core/views/admin.py`, `auth.py`

**What:** Django's `ModelForm` provides the template method skeleton:
`is_valid()` → `clean()` → `save()`. Each form subclass overrides only the
steps it needs (e.g. `CourseForm` sets `fields`, `widgets`; `ChapterForm`
adds an `order` field). Views call the standard skeleton without knowing
the form's internal logic.

---

### 2.5 Repository Pattern (lightweight, via Custom Managers)

**Where:** `UserManager` in `core/models.py`; service-layer query methods

**What:** Django's `Model.objects` manager already implements the Repository
pattern (a collection-like interface to the database). We extend it:

- `UserManager.create_user` and `create_superuser` encapsulate the
  creation logic (email normalisation, password hashing).
- Service methods such as `UserService.get_assigned_learners` encapsulate
  complex queries so views never write raw ORM code.

A full Repository abstraction (abstract base classes) was deliberately *not*
introduced because Django's ORM already provides a consistent interface and
adding another indirection layer would be over-engineering for this project size.

---

### 2.6 Facade Pattern

**Where:** `core/services/__init__.py` and `core/views/__init__.py`

**What:** Both `__init__.py` files act as **Facades** — they expose a flat,
simplified import surface that hides the internal sub-module structure.

```python
# Caller sees one flat namespace:
from core.services import ProgressService, MessageService

# Internal structure is hidden:
# core/services/progress.py, core/services/messaging.py, ...
```

`core/views/__init__.py` re-exports every view callable so that `core/urls.py`
can use the unchanged `from . import views` syntax. Consumers of the URL module
are unaffected by the internal split into sub-modules.

---

## 3. SOLID Principles

### S — Single Responsibility Principle

Every module has one reason to change:

| Module | Sole responsibility |
|---|---|
| `views/auth.py` | HTTP login/register/logout flow |
| `views/learner.py` | HTTP responses for learner pages |
| `services/progress.py` | Computing and querying learner progress |
| `services/messaging.py` | Chat authorization and message persistence |
| `services/course.py` | Course/chapter CRUD and captioning |
| `services/user.py` | User deletion and mentor-assignment logic |
| `models.py` | Database schema and model-level behaviour |
| `forms.py` | Input validation and HTML widget configuration |
| `utils.py` | Image captioning I/O |

If business rules for progress change, only `services/progress.py` is touched.
If the chat UI changes, only `views/learner.py` and `chat.html` are touched.

---

### O — Open/Closed Principle

**`role_required` decorator:**
Adding a new role (e.g. `"teaching_assistant"`) requires no modification to
the decorator itself — it works for any string role. The decorator is
*open for extension* (new roles) and *closed for modification*.

**`CourseService` captioner:**
Swapping the captioning model (e.g. from GIT-base to BLIP-2) requires only
passing a different callable to `CourseService()`. No internal code changes.

---

### L — Liskov Substitution Principle

The `captioner` injectable in `CourseService` is typed as `Callable[[str], str]`.
Any function with that signature is a valid substitution — a stub, a mock, a
different ML model, or even a hardcoded string function. All substitutes behave
correctly from the caller's perspective.

Django's `AbstractBaseUser` is itself an LSP example: `User` substitutes
cleanly wherever Django expects an `AbstractBaseUser` instance (auth middleware,
`request.user`, permission checks).

---

### I — Interface Segregation Principle

Services are deliberately narrow in scope. A view that only needs progress data
imports `ProgressService`; it is not forced to depend on `MessageService` or
`CourseService`. Compare with the pre-refactor `views.py`, which imported
everything into a single 250-line file.

Similarly, AJAX views in `api.py` depend only on `MessageService` — they have
no knowledge of courses or progress.

---

### D — Dependency Inversion Principle

High-level policy (views) depends on service abstractions, not on ORM details:

```
view (high level)
   ↓ calls
service method (abstraction)
   ↓ queries
Django ORM (low-level detail)
```

`CourseService`'s constructor-injected captioner is the clearest example:
the service depends on a callable abstraction, not on the concrete HuggingFace
import.

---

## 4. Exception Handling

### Strategy

The platform uses **domain exceptions at the service boundary** and translates
them into user-facing messages at the view boundary. No raw database exceptions
or Django-internal exceptions are surfaced to templates.

```
Service raises              View catches and translates
──────────────              ──────────────────────────
ValueError              →   flash.error(request, str(exc))
PermissionError         →   flash.error(request, str(exc)) + redirect
User.DoesNotExist       →   flash.error(request, "User not found.")
json.JSONDecodeError    →   JsonResponse({"error": "..."}, status=400)
Unexpected Exception    →   logger.exception(...) + 500 JSON response
```

### View-level handling (`core/views/admin.py`)

```python
try:
    email = UserService.delete_user(actor=request.user, target=target)
    flash.success(request, f"User {email} has been removed.")
except User.DoesNotExist:
    flash.error(request, "User not found.")
except PermissionError as exc:
    flash.error(request, str(exc))
```

Advantages:
- Service methods have clean, readable signatures (no `request` needed).
- Error messages are defined once in the service (`"Admins cannot be deleted"`),
  not scattered across views.
- Unit tests can verify error conditions by asserting on the exception type
  rather than parsing HTML responses.

### API-level handling (`core/views/api.py`)

AJAX endpoints return structured JSON errors with appropriate HTTP status codes:

| Scenario | Status | Body |
|---|---|---|
| Malformed JSON body | 400 | `{"error": "Invalid request body."}` |
| Empty message content | 400 | `{"error": "Message content cannot be empty."}` |
| Authorization violation | 403 | `{"error": "<reason>"}` |
| Unexpected server error | 500 | `{"error": "An unexpected error occurred."}` |

The 500 path also logs the full traceback via `logger.exception(...)` so it
appears in server logs without leaking stack traces to the browser.

### Input validation

- **Forms:** Django `ModelForm` and `Form` handle field-level validation
  (required fields, email format, password confirmation). Errors are displayed
  inline in templates via `{{ form.field.errors }}`.
- **Services:** validate business-level constraints (non-empty title, valid role)
  and raise `ValueError` with a human-readable message.
- **URL parameters:** `get_object_or_404` handles invalid PKs cleanly (returns
  404 rather than a 500 `DoesNotExist` exception).
- **POST ID inputs:** before calling `int()`, views check `raw_id.isdigit()` to
  prevent `ValueError` on malformed form submissions.

---

## 5. CSRF Protection

### Mechanism

Django's `CsrfViewMiddleware` is active (listed in `MIDDLEWARE` in `settings.py`).
It sets a `csrftoken` cookie on every response and validates a matching token on
every unsafe HTTP method (`POST`, `PUT`, `PATCH`, `DELETE`).

### HTML Forms

Every `<form method="post">` in every template includes `{% csrf_token %}`,
which renders a hidden `<input type="hidden" name="csrfmiddlewaretoken" value="...">`.
Django validates this token server-side before the view body runs.

```html
<form method="post" action="{% url 'admin_assign_mentor' learner.id %}">
  {% csrf_token %}
  ...
</form>
```

### AJAX (chat send, chapter complete)

AJAX `POST` requests (from `chat.html` and `chapter_view.html`) read the
`csrftoken` cookie and send it as the `X-CSRFToken` request header — the
standard Django-recommended pattern:

```javascript
function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

fetch('/api/messages/send/', {
    method: 'POST',
    headers: {
        'Content-Type':     'application/json',
        'X-CSRFToken':      getCookie('csrftoken'),
    },
    body: JSON.stringify({ receiver_id: PARTNER_ID, content: content })
});
```

Django's middleware accepts both the form-field and the header variants, so no
special `@csrf_exempt` decoration is needed on any view.

### Why not exempt AJAX endpoints?

`@csrf_exempt` is intentionally avoided. Even pure JSON APIs are vulnerable to
CSRF if cookies carry the session credential (which they do here, via Django's
session middleware). The token-in-header approach costs one extra `getCookie()`
call and provides strong protection.

---

## 6. Text-to-Speech: Method, Library & Rationale

### What is read aloud

When a learner opens a chapter, the platform can read:

1. **The chapter's text content** (`Chapter.content` field).
2. **The AI-generated image description** (`Chapter.image_description` field),
   prefixed with "Image description:" — so visually-impaired learners receive
   full context for embedded visuals.

Both pieces of text are concatenated into a single utterance.

### Library used: Web Speech API (`SpeechSynthesis`)

```javascript
var utterance  = new SpeechSynthesisUtterance(fullText);
utterance.rate = 0.95;   // slightly slower for comprehension
utterance.lang = 'en-US';
window.speechSynthesis.speak(utterance);
```

**Reference:** [MDN SpeechSynthesis](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis)

### Why the Web Speech API rather than a server-side TTS model?

The provided `courses/read.py` used `microsoft/speecht5_tts` (a HuggingFace
model) to generate `.wav` files server-side. This approach works well in a
local research/notebook context but has several practical drawbacks for a
deployed web application:

| Concern | Server-side SpeechT5 | Browser Web Speech API |
|---|---|---|
| **Model size** | ~400 MB download per server | Zero — uses OS/browser voice |
| **Latency** | Seconds per chapter (GPU helps, CPU is slow) | Instantaneous |
| **Server cost** | Requires GPU instance for real-time use | Free — runs on client |
| **Storage** | Generates `.wav`/`.mp3` files that must be stored | No files stored |
| **Voice quality** | High (neural TTS) | Good (system TTS, varies by OS) |
| **Offline support** | Requires server | Works offline if content is cached |
| **Accessibility** | Custom implementation needed | Screen readers already familiar with browser TTS |

For this platform's audience (BVI learners), **latency and reliability** are
paramount. A learner who presses Read Aloud must hear audio immediately. The Web
Speech API provides this with zero infrastructure cost.

### Trigger mechanism

Reading is triggered by:

- Clicking the **"🔊 Read Aloud"** button (accessible via keyboard Tab/Enter).
- Pressing **`Ctrl+R`** (the shortcut mentioned in the original spec). The
  default browser "refresh" action is suppressed via `e.preventDefault()`.

```javascript
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        isReading ? stopReading() : startReading();
    }
});
```

A "Stop" button and status indicator (`aria-live="polite"`) provide accessible
feedback during playback.

### Server-side TTS (original `read.py`) — retained as reference

`courses/read.py` (from the original codebase) is preserved as a reference
implementation showing how to generate WAV/MP3 files offline using SpeechT5.
It is not wired into the live platform but can be used as a batch pre-generation
tool if high-quality offline audio files are required in the future.

---

## 7. Image Captioning Pipeline

When an admin uploads a chapter image, the following sequence runs synchronously
in the request cycle:

```
Admin uploads image
       │
       ▼
Django saves file to MEDIA_ROOT/chapter_images/<filename>
       │
       ▼
CourseService.create_chapter() calls self._captioner(chapter.image.path)
       │
       ▼
utils.generate_image_caption(image_path)
  ├─ Loads microsoft/git-base-coco (HuggingFace)
  ├─ Runs model.generate() on the image
  └─ Returns caption string (e.g. "a diagram of a neural network")
       │
       ▼
chapter.image_description = caption
chapter.save(update_fields=["image_description"])
       │
       ▼
Caption stored in DB, served to learner via chapter_view.html
and read aloud as part of the TTS utterance
```

**Model:** `microsoft/git-base-coco` — a GIT (Generative Image-to-Text)
model fine-tuned on MS-COCO. Chosen because:
- Small enough to run on CPU (unlike larger vision-language models).
- Good accuracy on diagrams, charts, and photographs common in STEM content.
- Available via `transformers` with a two-line load.

**Fallback:** If `transformers` or `torch` is not installed, `utils.py` catches
the `ImportError` and returns a placeholder string. Chapters are fully functional
without the ML stack; the description field is simply empty.

---

## 8. Data Model Relationships

```
User (role: admin | mentor | learner)
│
├─── created_courses ──────────────────▶ Course
│                                            │
│                                            └─── chapters ──▶ Chapter
│                                                                  │
│                                            ChapterCompletion ◀───┤
│                                            (learner FK, chapter FK)│
│
├─── mentor_assignment (OneToOne) ─────▶ MentorAssignment
│    [learner side]                          ├─ mentor FK ──▶ User (mentor)
│                                            └─ assigned_by FK ▶ User (admin)
│
├─── sent_messages ────────────────────▶ Message
│    [sender FK]                             └─ receiver FK ──▶ User
│
└─── received_messages ────────────────▶ Message
     [receiver FK]
```

Key constraints:
- `MentorAssignment.learner` is `OneToOneField` — each learner has at most one mentor.
- `ChapterCompletion` has `unique_together = ('learner', 'chapter')` — idempotent completion marking.
- Admin accounts are protected from deletion at the service layer, not the DB layer (a deliberate application-level policy).

---

## 9. Request Lifecycle

### Standard page request (e.g. mentor progress view)

```
Browser GET /mentor/learner/42/progress/
       │
       ▼
Django URL router → views/mentor.py: mentor_learner_progress
       │
       ▼
@role_required("mentor") decorator
  ├─ @login_required: redirect to /login/ if not authenticated
  └─ role check: redirect to own dashboard if wrong role
       │
       ▼
get_object_or_404(User, pk=42, role="learner")  → 404 if not found
       │
       ▼
MessageService.assert_learner_assigned_to_mentor(mentor, learner)
  └─ PermissionError → flash + redirect to mentor_dashboard
       │
       ▼
ProgressService.build_learner_progress_for_mentor(learner)
  ├─ Fetches all courses
  ├─ Fetches completed_chapter_ids for learner (single query)
  └─ Builds snapshot list (no N+1 queries)
       │
       ▼
render(request, "core/mentor_learner_progress.html", context)
       │
       ▼
Browser receives HTML
```

### AJAX message send

```
Browser POST /api/messages/send/   (JSON body + X-CSRFToken header)
       │
       ▼
CsrfViewMiddleware validates token  → 403 if invalid
       │
       ▼
@require_POST  → 405 if not POST
@login_required → 302 to login if not authenticated
       │
       ▼
views/api.py: api_send_message
  ├─ json.loads(request.body) → 400 if malformed
  ├─ get_object_or_404(User, pk=receiver_id) → 404 if not found
  └─ MessageService.send_message(sender, receiver, content)
        ├─ ValueError (empty) → 400 JSON
        ├─ PermissionError (not allowed) → 403 JSON
        └─ Success → persists Message, returns JSON
       │
       ▼
Browser receives {"id":..., "sender_id":..., "content":..., "timestamp":...}
chat.html appendMessage() renders bubble without page reload
```
