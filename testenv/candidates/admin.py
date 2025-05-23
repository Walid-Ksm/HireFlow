from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Candidate, JobApplication, EmailVerification


# Unregister the provided model admin
admin.site.unregister(User)

# Define a new User admin that doesn't enforce email uniqueness
class UserAdmin(BaseUserAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Make email field not unique
        form.base_fields['email'].unique = False
        return form

# Re-register UserAdmin
admin.site.register(User, UserAdmin)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'is_email_verified', 'created_at')
    list_filter = ('is_email_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'skills')
    date_hierarchy = 'created_at'


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('candidate__user__username', 'job__title')
    date_hierarchy = 'created_at'


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'is_verified')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'created_at'
