from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/category/<int:category_id>/', views.jobs_by_category, name='jobs_by_category'),
    path('jobs/location/<int:location_id>/', views.jobs_by_location, name='jobs_by_location'),
    path('jobs/type/<str:contract_type>/', views.jobs_by_type, name='jobs_by_type'),
    path('search/', views.job_search, name='job_search'),
] 