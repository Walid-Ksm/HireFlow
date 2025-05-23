from django.urls import path
from . import views

app_name = 'recruiters'

urlpatterns = [
    path('register/', views.recruiter_register, name='register'),
    path('login/', views.recruiter_login, name='login'),
    path('logout/', views.recruiter_logout, name='logout'),
    path('dashboard/', views.recruiter_dashboard, name='dashboard'),
    path('profile/', views.recruiter_profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.create_job, name='create_job'),
    path('jobs/<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('jobs/<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('jobs/<int:job_id>/applications/', views.job_applications, name='job_applications'),
    path('applications/<int:application_id>/', views.application_detail, name='application_detail'),
    path('applications/<int:application_id>/update-status/', views.update_application_status, name='update_application_status'),
    path('candidates/<int:candidate_id>/notes/', views.candidate_notes, name='candidate_notes'),
    path('candidates/<int:candidate_id>/add-note/', views.add_candidate_note, name='add_candidate_note'),
    path('stats/', views.recruitment_stats, name='stats'),
    path('export/<int:job_id>/applications/', views.export_applications, name='export_applications'),
] 