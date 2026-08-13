from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'rank', 'region', 'prison_station', 'is_active')
    list_filter = ('is_active', 'role', 'rank', 'region', 'prison_station')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Assignment', {'fields': ('role', 'rank', 'region', 'prison_station', 'must_change_password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'role', 'rank',
                       'region', 'prison_station', 'password1', 'password2', 'is_staff', 'is_active')}
         ),
    )
