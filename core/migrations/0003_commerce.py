"""
Migration: Add price to Course, add CartItem, Enrollment, Transaction
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_courses_and_features'),
    ]

    operations = [
        # Add price field to Course
        migrations.AddField(
            model_name='course',
            name='price',
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text='Set to 0.00 for a free course.',
                max_digits=8,
            ),
        ),

        # CartItem
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cart_items',
                    to='core.course',
                )),
                ('learner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cart_items',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-added_at'],
                'unique_together': {('learner', 'course')},
            },
        ),

        # Enrollment
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='enrollments',
                    to='core.course',
                )),
                ('learner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='enrollments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-enrolled_at'],
                'unique_together': {('learner', 'course')},
            },
        ),

        # Transaction
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('success', 'Success'),
                        ('failed', 'Failed'),
                        ('cancelled', 'Cancelled'),
                    ],
                    default='pending',
                    max_length=12,
                )),
                ('transaction_ref', models.CharField(max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('courses', models.ManyToManyField(
                    blank=True,
                    related_name='transactions',
                    to='core.course',
                )),
                ('learner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transactions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
