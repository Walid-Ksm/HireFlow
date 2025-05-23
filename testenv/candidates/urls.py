from django.urls import path
from . import views

app_name = 'candidates'

urlpatterns = [
    path('register/', views.candidate_register, name='register'),
    path('login/', views.candidate_login, name='login'),
    path('logout/', views.candidate_logout, name='logout'),
    path('dashboard/', views.candidate_dashboard, name='dashboard'),
    path('profile/', views.candidate_profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('applications/', views.application_list, name='applications'),
    path('apply/<int:job_id>/', views.apply_job, name='apply_job'),
    path('application/<int:application_id>/', views.application_detail, name='application_detail'),
    path('application/<int:application_id>/edit/', views.edit_application, name='edit_application'),
    path('application/<int:application_id>/delete/', views.delete_application, name='delete_application'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
] 