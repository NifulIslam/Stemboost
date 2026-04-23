"""
Migration: Add Course, Chapter, MentorAssignment, ChapterCompletion, Message
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    limit_choices_to={'role': 'admin'},
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_courses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Chapter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('image', models.ImageField(blank=True, null=True, upload_to='chapter_images/')),
                ('image_description', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chapters',
                    to='core.course',
                )),
            ],
            options={'ordering': ['order', 'created_at']},
        ),
        migrations.CreateModel(
            name='MentorAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now=True)),
                ('assigned_by', models.ForeignKey(
                    limit_choices_to={'role': 'admin'},
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assignments_made',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('learner', models.OneToOneField(
                    limit_choices_to={'role': 'learner'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='mentor_assignment',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('mentor', models.ForeignKey(
                    limit_choices_to={'role': 'mentor'},
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assigned_learners',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'Mentor Assignment'},
        ),
        migrations.CreateModel(
            name='ChapterCompletion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('chapter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='completions',
                    to='core.chapter',
                )),
                ('learner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='completions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'unique_together': {('learner', 'chapter')}},
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('sender', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sent_messages',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('receiver', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='received_messages',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['timestamp']},
        ),
    ]
