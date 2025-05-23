from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import JobPost, JobCategory, JobLocation


def home(request):
    """Home page view with featured jobs and categories"""
    # Get featured jobs (open jobs, ordered by creation date)
    featured_jobs = JobPost.objects.filter(status='OP').order_by('-created_at')[:6]
    
    # Get job categories with job count
    job_categories = JobCategory.objects.annotate(
        count=Count('jobpost', filter=Q(jobpost__status='OP'))
    ).filter(count__gt=0)[:8]
    
    # Add icon classes for categories (for display purposes)
    icons = ['briefcase', 'code', 'chart-line', 'hospital', 'graduation-cap', 
             'tools', 'utensils', 'shopping-cart', 'landmark', 'palette']
    
    for i, category in enumerate(job_categories):
        category.icon = icons[i % len(icons)]
    
    context = {
        'featured_jobs': featured_jobs,
        'job_categories': job_categories,
    }
    
    return render(request, 'jobs/home.html', context)


def job_list(request):
    """List all active job posts with filtering options"""
    jobs = JobPost.objects.filter(status='OP').order_by('-created_at')
    
    # Get filter parameters
    category_id = request.GET.get('category')
    location_id = request.GET.get('location')
    contract_type = request.GET.get('type')
    
    # Apply filters if provided
    if category_id:
        jobs = jobs.filter(category_id=category_id)
    
    if location_id:
        jobs = jobs.filter(location_id=location_id)
    
    if contract_type:
        jobs = jobs.filter(contract_type=contract_type)
    
    # Get all categories and locations for the filter form
    categories = JobCategory.objects.all()
    locations = JobLocation.objects.all()
    
    context = {
        'jobs': jobs,
        'categories': categories,
        'locations': locations,
        'contract_types': JobPost.CONTRACT_TYPES,
        'selected_category': int(category_id) if category_id else None,
        'selected_location': int(location_id) if location_id else None,
        'selected_type': contract_type if contract_type else None,
    }
    
    return render(request, 'jobs/job_list.html', context)


def job_detail(request, job_id):
    """Show detailed information about a specific job"""
    job = get_object_or_404(JobPost, id=job_id)
    
    # Get similar jobs (same category or location)
    similar_jobs = JobPost.objects.filter(
        Q(category=job.category) | Q(location=job.location),
        status='OP'
    ).exclude(id=job.id).distinct()[:3]
    
    context = {
        'job': job,
        'similar_jobs': similar_jobs,
    }
    
    return render(request, 'jobs/job_detail.html', context)


def jobs_by_category(request, category_id):
    """Filter jobs by category"""
    category = get_object_or_404(JobCategory, id=category_id)
    return redirect(f"{reverse('jobs:job_list')}?category={category_id}")


def jobs_by_location(request, location_id):
    """Filter jobs by location"""
    location = get_object_or_404(JobLocation, id=location_id)
    return redirect(f"{reverse('jobs:job_list')}?location={location_id}")


def jobs_by_type(request, contract_type):
    """Filter jobs by contract type"""
    return redirect(f"{reverse('jobs:job_list')}?type={contract_type}")


def job_search(request):
    """Search jobs by keyword and/or location"""
    # Get parameters and handle duplicates by taking the first non-None value
    keyword = request.GET.get('keyword', '')
    location = request.GET.get('location', '')
    category_id = request.GET.getlist('category')[0] if request.GET.getlist('category') else None
    contract_type = request.GET.getlist('contract_type')[0] if request.GET.getlist('contract_type') else None
    min_salary = request.GET.getlist('min_salary')[0] if request.GET.getlist('min_salary') else None
    date_posted = request.GET.get('date_posted')
    sort = request.GET.get('sort', 'newest')
    
    # Start with all open jobs
    jobs = JobPost.objects.filter(status='OP')
    
    # Apply keyword search if provided
    if keyword:
        jobs = jobs.filter(
            Q(title__icontains=keyword) | 
            Q(company_name__icontains=keyword) | 
            Q(description__icontains=keyword) |
            Q(category__name__icontains=keyword)
        )
    
    # Apply location search if provided
    if location:
        jobs = jobs.filter(
            Q(location__city__icontains=location) |
            Q(location__state__icontains=location) |
            Q(location__country__icontains=location)
        )
    
    # Apply category filter
    if category_id and category_id != 'None':
        try:
            category_id = int(category_id)
            jobs = jobs.filter(category_id=category_id)
        except (ValueError, TypeError):
            pass
    
    # Apply contract type filter
    if contract_type and contract_type != 'None':
        jobs = jobs.filter(contract_type=contract_type)
    
    # Apply salary filter
    if min_salary and min_salary != 'None':
        try:
            min_salary = float(min_salary)
            jobs = jobs.filter(salary_min__gte=min_salary)
        except (ValueError, TypeError):
            pass
    
    # Apply date posted filter
    if date_posted and date_posted != 'None':
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        if date_posted == 'today':
            jobs = jobs.filter(created_at__date=today)
        elif date_posted == 'week':
            week_ago = today - timedelta(days=7)
            jobs = jobs.filter(created_at__date__gte=week_ago)
        elif date_posted == 'month':
            month_ago = today - timedelta(days=30)
            jobs = jobs.filter(created_at__date__gte=month_ago)
    
    # Apply sorting
    if sort == 'oldest':
        jobs = jobs.order_by('created_at')
    elif sort == 'salary_high':
        jobs = jobs.order_by('-salary_max')
    elif sort == 'salary_low':
        jobs = jobs.order_by('salary_min')
    else:  # newest
        jobs = jobs.order_by('-created_at')
    
    # Get all categories and contract types for the filter form
    categories = JobCategory.objects.all()
    contract_types = JobPost.CONTRACT_TYPES
    
    context = {
        'jobs': jobs,
        'keyword': keyword,
        'location': location,
        'categories': categories,
        'contract_types': contract_types,
        'selected_category': int(category_id) if category_id and category_id != 'None' else None,
        'selected_type': contract_type if contract_type and contract_type != 'None' else None,
        'min_salary': min_salary if min_salary and min_salary != 'None' else None,
        'date_posted': date_posted if date_posted and date_posted != 'None' else None,
        'sort': sort,
        'sort_display': {
            'newest': 'Newest first',
            'oldest': 'Oldest first',
            'salary_high': 'Highest salary',
            'salary_low': 'Lowest salary'
        }.get(sort, 'Newest first')
    }
    
    return render(request, 'jobs/job_search.html', context)
