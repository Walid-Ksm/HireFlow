from django.contrib import admin
from .models import JobCategory, JobLocation, JobPost


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(JobLocation)
class JobLocationAdmin(admin.ModelAdmin):
    list_display = ('city', 'state', 'country')
    search_fields = ('city', 'state', 'country')


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'company_name', 'category', 'contract_type', 'status', 'created_at')
    list_filter = ('status', 'contract_type', 'category', 'created_at')
    search_fields = ('title', 'company_name', 'description')
    date_hierarchy = 'created_at'
    raw_id_fields = ('posted_by',)
