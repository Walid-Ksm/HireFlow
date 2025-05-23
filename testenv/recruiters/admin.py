from django.contrib import admin
from .models import Recruiter, CandidateNote


@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'phone_number', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('company_name', 'user__username', 'user__email')
    date_hierarchy = 'created_at'


@admin.register(CandidateNote)
class CandidateNoteAdmin(admin.ModelAdmin):
    list_display = ('recruiter', 'candidate', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('recruiter__company_name', 'candidate__user__username', 'content')
    date_hierarchy = 'created_at'
    raw_id_fields = ('recruiter', 'candidate')
