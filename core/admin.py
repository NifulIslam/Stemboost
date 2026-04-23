from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('userid', 'email', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter   = ('role', 'is_active', 'is_staff')
    search_fields = ('email',)
    ordering      = ('-date_joined',)
    readonly_fields = ('userid', 'date_joined')

    fieldsets = (
        (None,          {'fields': ('email', 'password')}),
        ('Role',        {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Metadata',    {'fields': ('userid', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('email', 'role', 'password1', 'password2'),
        }),
    )
