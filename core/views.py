"""
STEMboost Views — full feature set
"""
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse
from django.db.models import Q

from .models import User, Course, Chapter, MentorAssignment, ChapterCompletion, Message
from .forms import LoginForm, RegisterForm, CourseForm, ChapterForm
from .utils import generate_image_caption


# ── Helpers ──────────────────────────────────────────────────────────────────

def _redirect_by_role(user):
    return redirect(user.get_dashboard_url())


def _role_required(role):
    def decorator(view_func):
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                return _redirect_by_role(request.user)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def _compute_progress(learner, course):
    """Return integer 0-100 for learner's progress in a course."""
    total = course.chapters.count()
    if total == 0:
        return 0
    done = ChapterCompletion.objects.filter(
        learner=learner, chapter__course=course
    ).count()
    return round((done / total) * 100)


# ── Landing ───────────────────────────────────────────────────────────────────

def landing(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    return render(request, 'core/landing.html')


# ── Login ─────────────────────────────────────────────────────────────────────

@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    form = LoginForm(request.POST or None)
    error_message = None

    if request.method == 'POST' and form.is_valid():
        email    = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user     = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return _redirect_by_role(user)
            else:
                error_message = 'Your account has been disabled. Please contact support.'
        else:
            error_message = 'Invalid email address or password. Please try again.'

    return render(request, 'core/login.html', {
        'form': form,
        'error_message': error_message,
        'page_name': 'Login Page',
    })


# ── Register ──────────────────────────────────────────────────────────────────

@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    form = RegisterForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return _redirect_by_role(user)

    return render(request, 'core/register.html', {
        'form': form,
        'page_name': 'Registration Page',
    })


# ── Logout ────────────────────────────────────────────────────────────────────

def logout_view(request):
    logout(request)
    return redirect('/')


# ══════════════════════════════════════════════════════════════════════════════
# LEARNER VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@_role_required('learner')
def learner_dashboard(request):
    learner = request.user
    query   = request.GET.get('q', '').strip()

    courses_qs = Course.objects.prefetch_related('chapters')
    if query:
        courses_qs = courses_qs.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    completed_chapter_ids = set(
        ChapterCompletion.objects.filter(learner=learner)
        .values_list('chapter_id', flat=True)
    )

    courses_data = []
    for course in courses_qs:
        chapters_list = list(course.chapters.order_by('order', 'id'))
        progress = _compute_progress(learner, course)
        courses_data.append({
            'id':            course.id,
            'title':         course.title,
            'description':   course.description,
            'progress':      progress,
            'chapter_count': len(chapters_list),
            'chapters':      [
                {
                    'id':           ch.id,
                    'title':        ch.title,
                    'is_completed': ch.id in completed_chapter_ids,
                }
                for ch in chapters_list
            ],
        })

    # Mentor assignment
    try:
        assignment = learner.mentor_assignment
        mentor     = assignment.mentor
    except MentorAssignment.DoesNotExist:
        mentor = None

    # Stats
    total_courses    = Course.objects.count()
    completed_count  = sum(1 for c in courses_data if c['progress'] == 100)
    overall_progress = (
        round(sum(c['progress'] for c in courses_data) / len(courses_data))
        if courses_data else 0
    )

    return render(request, 'core/dashboard_learner.html', {
        'page_name':       'Learner Dashboard',
        'user':            learner,
        'courses':         courses_data,
        'query':           query,
        'mentor':          mentor,
        'total_courses':   total_courses,
        'completed_count': completed_count,
        'overall_progress': overall_progress,
    })


@_role_required('learner')
def chapter_view(request, chapter_id):
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    learner = request.user

    # Check if already completed
    is_completed = ChapterCompletion.objects.filter(
        learner=learner, chapter=chapter
    ).exists()

    # All chapters in same course for navigation
    course_chapters = list(chapter.course.chapters.order_by('order', 'id'))
    current_index   = next((i for i, c in enumerate(course_chapters) if c.id == chapter.id), 0)
    prev_chapter    = course_chapters[current_index - 1] if current_index > 0 else None
    next_chapter    = course_chapters[current_index + 1] if current_index < len(course_chapters) - 1 else None

    return render(request, 'core/chapter_view.html', {
        'page_name':       f'Chapter: {chapter.title}',
        'chapter':         chapter,
        'course':          chapter.course,
        'is_completed':    is_completed,
        'prev_chapter':    prev_chapter,
        'next_chapter':    next_chapter,
        'user':            learner,
    })


@require_POST
@login_required
def mark_chapter_complete(request, chapter_id):
    if request.user.role != 'learner':
        return JsonResponse({'error': 'Forbidden'}, status=403)

    chapter = get_object_or_404(Chapter, pk=chapter_id)
    ChapterCompletion.objects.get_or_create(learner=request.user, chapter=chapter)
    progress = _compute_progress(request.user, chapter.course)
    return JsonResponse({'progress': progress, 'ok': True})


@_role_required('learner')
def learner_chat(request):
    learner = request.user
    try:
        mentor = learner.mentor_assignment.mentor
    except MentorAssignment.DoesNotExist:
        mentor = None

    if not mentor:
        return render(request, 'core/chat.html', {
            'page_name': 'Chat',
            'user':      learner,
            'partner':   None,
            'messages':  [],
            'no_mentor': True,
        })

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(sender=learner, receiver=mentor, content=content)
        return redirect('learner_chat')

    msgs = Message.objects.filter(
        Q(sender=learner, receiver=mentor) |
        Q(sender=mentor,  receiver=learner)
    ).order_by('timestamp')
    # mark received as read
    msgs.filter(receiver=learner, is_read=False).update(is_read=True)

    return render(request, 'core/chat.html', {
        'page_name': 'Chat with Mentor',
        'user':      learner,
        'partner':   mentor,
        'messages':  msgs,
        'no_mentor': False,
    })


# ── AJAX: poll new messages ───────────────────────────────────────────────────

@login_required
def api_messages(request, partner_id):
    partner = get_object_or_404(User, pk=partner_id)
    me      = request.user

    msgs = Message.objects.filter(
        Q(sender=me, receiver=partner) |
        Q(sender=partner, receiver=me)
    ).order_by('timestamp').values(
        'id', 'sender_id', 'content', 'timestamp', 'is_read'
    )

    Message.objects.filter(receiver=me, sender=partner, is_read=False).update(is_read=True)

    return JsonResponse({'messages': list(msgs)}, json_dumps_params={'default': str})


@require_POST
@login_required
def api_send_message(request):
    try:
        data     = json.loads(request.body)
        receiver = get_object_or_404(User, pk=data['receiver_id'])
        content  = data.get('content', '').strip()
        if not content:
            return JsonResponse({'error': 'Empty message'}, status=400)

        # Security: learner can only message their mentor; mentor can only message assigned learner
        me = request.user
        if me.role == 'learner':
            try:
                allowed = me.mentor_assignment.mentor
            except MentorAssignment.DoesNotExist:
                return JsonResponse({'error': 'No mentor assigned'}, status=403)
            if receiver.id != allowed.id:
                return JsonResponse({'error': 'Forbidden'}, status=403)
        elif me.role == 'mentor':
            assigned = MentorAssignment.objects.filter(mentor=me, learner=receiver).exists()
            if not assigned:
                return JsonResponse({'error': 'Forbidden'}, status=403)

        msg = Message.objects.create(sender=me, receiver=receiver, content=content)
        return JsonResponse({
            'id':        msg.id,
            'sender_id': msg.sender_id,
            'content':   msg.content,
            'timestamp': msg.timestamp.isoformat(),
        })
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Bad request'}, status=400)


# ══════════════════════════════════════════════════════════════════════════════
# MENTOR VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@_role_required('mentor')
def mentor_dashboard(request):
    mentor   = request.user
    assignments = MentorAssignment.objects.filter(mentor=mentor).select_related('learner')
    learners = [a.learner for a in assignments]

    return render(request, 'core/dashboard_mentor.html', {
        'page_name':     'Mentor Dashboard',
        'user':          mentor,
        'learners':      learners,
        'learner_count': len(learners),
    })


@_role_required('mentor')
def mentor_chat(request, learner_id):
    mentor  = request.user
    learner = get_object_or_404(User, pk=learner_id, role='learner')

    # Confirm this learner is actually assigned to this mentor
    if not MentorAssignment.objects.filter(mentor=mentor, learner=learner).exists():
        messages.error(request, 'This learner is not assigned to you.')
        return redirect('mentor_dashboard')

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(sender=mentor, receiver=learner, content=content)
        return redirect('mentor_chat', learner_id=learner_id)

    msgs = Message.objects.filter(
        Q(sender=mentor, receiver=learner) |
        Q(sender=learner, receiver=mentor)
    ).order_by('timestamp')
    msgs.filter(receiver=mentor, is_read=False).update(is_read=True)

    return render(request, 'core/chat.html', {
        'page_name': f'Chat with {learner.email}',
        'user':      mentor,
        'partner':   learner,
        'messages':  msgs,
        'no_mentor': False,
    })


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@_role_required('admin')
def admin_dashboard(request):
    all_users = User.objects.all().order_by('role', 'date_joined')
    learners  = User.objects.filter(role='learner')
    mentors   = User.objects.filter(role='mentor')
    admins    = User.objects.filter(role='admin')
    courses   = Course.objects.all()

    # Build learner list with mentor info
    learner_data = []
    for learner in learners:
        try:
            assigned_mentor = learner.mentor_assignment.mentor
        except MentorAssignment.DoesNotExist:
            assigned_mentor = None
        learner_data.append({'user': learner, 'mentor': assigned_mentor})

    context = {
        'page_name':      'Admin Dashboard',
        'user':           request.user,
        'all_users':      all_users,
        'learner_data':   learner_data,
        'mentors':        mentors,
        'courses':        courses,
        'total_users':    all_users.count(),
        'total_learners': learners.count(),
        'total_mentors':  mentors.count(),
        'total_admins':   admins.count(),
        'total_courses':  courses.count(),
    }
    return render(request, 'core/dashboard_admin.html', context)


@_role_required('admin')
@require_POST
def admin_delete_user(request):
    try:
        target_id = int(request.POST['delete_user_id'])
        target    = User.objects.get(id=target_id)

        if target.id == request.user.id:
            messages.error(request, 'You cannot delete your own account.')
        elif target.role == 'admin':
            messages.error(request, 'Admins cannot delete other admin accounts.')
        else:
            email = target.email
            target.delete()
            messages.success(request, f'User {email} has been removed.')
    except (User.DoesNotExist, ValueError, KeyError):
        messages.error(request, 'User not found.')
    return redirect('admin_dashboard')


@_role_required('admin')
@require_POST
def admin_assign_mentor(request, learner_id):
    learner   = get_object_or_404(User, pk=learner_id, role='learner')
    mentor_id = request.POST.get('mentor_id')

    if not mentor_id:
        messages.error(request, 'Please select a mentor.')
        return redirect('admin_dashboard')

    mentor = get_object_or_404(User, pk=mentor_id, role='mentor')
    MentorAssignment.objects.update_or_create(
        learner=learner,
        defaults={'mentor': mentor, 'assigned_by': request.user}
    )
    messages.success(request, f'{learner.email} has been assigned to mentor {mentor.email}.')
    return redirect('admin_dashboard')


# ── Course Management ─────────────────────────────────────────────────────────

@_role_required('admin')
def admin_course_create(request):
    form = CourseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.created_by = request.user
        course.save()
        messages.success(request, f'Course "{course.title}" created.')
        return redirect('admin_course_edit', course_id=course.id)

    return render(request, 'core/course_form.html', {
        'page_name': 'Create Course',
        'form':      form,
        'action':    'Create',
        'user':      request.user,
    })


@_role_required('admin')
def admin_course_edit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    form   = CourseForm(request.POST or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Course updated.')
        return redirect('admin_course_edit', course_id=course.id)

    chapters = course.chapters.order_by('order', 'id')
    return render(request, 'core/course_form.html', {
        'page_name': f'Edit Course — {course.title}',
        'form':      form,
        'course':    course,
        'chapters':  chapters,
        'action':    'Save Changes',
        'user':      request.user,
    })


@_role_required('admin')
@require_POST
def admin_course_delete(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    title  = course.title
    course.delete()
    messages.success(request, f'Course "{title}" deleted.')
    return redirect('admin_dashboard')


# ── Chapter Management ────────────────────────────────────────────────────────

@_role_required('admin')
def admin_chapter_create(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    form   = ChapterForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        chapter        = form.save(commit=False)
        chapter.course = course
        chapter.save()

        # Auto-generate image description
        if chapter.image:
            caption = generate_image_caption(chapter.image.path)
            chapter.image_description = caption
            chapter.save(update_fields=['image_description'])

        messages.success(request, f'Chapter "{chapter.title}" added.')
        return redirect('admin_course_edit', course_id=course.id)

    return render(request, 'core/chapter_form.html', {
        'page_name': 'Add Chapter',
        'form':      form,
        'course':    course,
        'action':    'Add Chapter',
        'user':      request.user,
    })


@_role_required('admin')
def admin_chapter_edit(request, chapter_id):
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    form    = ChapterForm(request.POST or None, request.FILES or None, instance=chapter)

    if request.method == 'POST' and form.is_valid():
        old_image = chapter.image.name if chapter.image else None
        chapter   = form.save()

        # Re-generate caption if a new image was uploaded
        if chapter.image and (chapter.image.name != old_image):
            caption = generate_image_caption(chapter.image.path)
            chapter.image_description = caption
            chapter.save(update_fields=['image_description'])

        messages.success(request, f'Chapter "{chapter.title}" updated.')
        return redirect('admin_course_edit', course_id=chapter.course.id)

    return render(request, 'core/chapter_form.html', {
        'page_name': f'Edit Chapter — {chapter.title}',
        'form':      form,
        'chapter':   chapter,
        'course':    chapter.course,
        'action':    'Save Changes',
        'user':      request.user,
    })


@_role_required('admin')
@require_POST
def admin_chapter_delete(request, chapter_id):
    chapter   = get_object_or_404(Chapter, pk=chapter_id)
    course_id = chapter.course.id
    chapter.delete()
    messages.success(request, 'Chapter deleted.')
    return redirect('admin_course_edit', course_id=course_id)
