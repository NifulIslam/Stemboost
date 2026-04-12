"""
STEMboost Models
- User: email-based auth, roles: learner | mentor | admin
- Course: admin-created courses
- Chapter: course subsections with text + image
- MentorAssignment: admin assigns mentor to learner
- ChapterCompletion: tracks which chapters a learner has read
- Message: direct chat between learner and assigned mentor
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ── User ─────────────────────────────────────────────────────────────────────

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, role='learner', **extra_fields):
        if not email:
            raise ValueError('An email address is required.')
        email = self.normalize_email(email.strip().lower())
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_LEARNER = 'learner'
    ROLE_MENTOR  = 'mentor'
    ROLE_ADMIN   = 'admin'

    ROLE_CHOICES = [
        (ROLE_LEARNER, 'Learner'),
        (ROLE_MENTOR,  'Mentor'),
        (ROLE_ADMIN,   'Admin'),
    ]

    id = models.BigAutoField(primary_key=True)

    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name='Email Address',
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_LEARNER,
        verbose_name='User Role',
    )

    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['role']

    class Meta:
        db_table = 'stemboost_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    @property
    def userid(self):
        return self.id

    @property
    def is_learner(self):
        return self.role == self.ROLE_LEARNER

    @property
    def is_mentor(self):
        return self.role == self.ROLE_MENTOR

    @property
    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN

    def get_dashboard_url(self):
        mapping = {
            self.ROLE_LEARNER: '/learner/',
            self.ROLE_MENTOR:  '/mentor/',
            self.ROLE_ADMIN:   '/admin-dashboard/',
        }
        return mapping.get(self.role, '/')

    def __str__(self):
        return f'{self.email} ({self.role})'


# ── Course ────────────────────────────────────────────────────────────────────

class Course(models.Model):
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_courses', limit_choices_to={'role': 'admin'}
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_chapter_count(self):
        return self.chapters.count()


# ── Chapter ───────────────────────────────────────────────────────────────────

class Chapter(models.Model):
    course            = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='chapters')
    title             = models.CharField(max_length=200)
    content           = models.TextField(help_text='Text content of this chapter')
    image             = models.ImageField(upload_to='chapter_images/', blank=True, null=True)
    image_description = models.TextField(
        blank=True,
        help_text='Auto-generated image description (populated when image is uploaded)'
    )
    order             = models.PositiveIntegerField(default=0)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.course.title} — {self.title}'


# ── Mentor Assignment ─────────────────────────────────────────────────────────

class MentorAssignment(models.Model):
    learner     = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='mentor_assignment',
        limit_choices_to={'role': 'learner'}
    )
    mentor      = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='assigned_learners',
        limit_choices_to={'role': 'mentor'}
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='assignments_made',
        limit_choices_to={'role': 'admin'}
    )
    assigned_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mentor Assignment'

    def __str__(self):
        return f'{self.learner.email} → {self.mentor.email if self.mentor else "none"}'


# ── Chapter Completion (progress tracking) ────────────────────────────────────

class ChapterCompletion(models.Model):
    learner      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completions')
    chapter      = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('learner', 'chapter')

    def __str__(self):
        return f'{self.learner.email} completed {self.chapter.title}'


# ── Message (learner ↔ mentor chat) ──────────────────────────────────────────

class Message(models.Model):
    sender    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content   = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read   = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'{self.sender.email} → {self.receiver.email}: {self.content[:40]}'
