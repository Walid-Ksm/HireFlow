from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q, Max
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import csv

from .models import Recruiter, CandidateNote
from candidates.models import Candidate, JobApplication
from jobs.models import JobPost, JobCategory, JobLocation
from notifications.models import Notification


def recruiter_register(request):
    """Register a new recruiter account"""
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        company_name = request.POST.get('company_name')
        
        # Validate form data
        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return redirect('recruiters:register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('recruiters:register')
        
        # Check if email is already used by a recruiter
        existing_user_with_email = User.objects.filter(email=email).first()
        if existing_user_with_email and Recruiter.objects.filter(user=existing_user_with_email).exists():
            messages.error(request, 'A recruiter account with this email already exists')
            return redirect('recruiters:register')
        
        # Create user and recruiter profile
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            recruiter = Recruiter.objects.create(user=user, company_name=company_name)
            
            # Log in the user
            login(request, user)
            messages.success(request, 'Account created successfully. Please complete your profile.')
            return redirect('recruiters:edit_profile')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('recruiters:register')
    
    return render(request, 'recruiters/register.html')


def recruiter_login(request):
    """Log in an existing recruiter"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user has a recruiter profile
            try:
                recruiter = Recruiter.objects.get(user=user)
                login(request, user)
                messages.success(request, 'Logged in successfully')
                return redirect('recruiters:dashboard')
            except Recruiter.DoesNotExist:
                messages.error(request, 'This account is not a recruiter account')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'recruiters/login.html')


def recruiter_logout(request):
    """Log out the recruiter"""
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('jobs:home')


@login_required
def recruiter_dashboard(request):
    """Show recruiter dashboard with stats and recent activities"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Get job posts by this recruiter
    job_posts = JobPost.objects.filter(posted_by=recruiter).order_by('-created_at')
    
    # Get recent applications across all jobs
    applications = JobApplication.objects.filter(job__posted_by=recruiter).order_by('-created_at')
    recent_applications = applications[:10]
    
    # Get application stats
    total_applications = applications.count()
    pending_applications = applications.filter(status='PE').count()
    reviewing_applications = applications.filter(status='RV').count()
    accepted_applications = applications.filter(status='AC').count()
    rejected_applications = applications.filter(status='RJ').count()
    
    # Get stats by job
    jobs_with_stats = job_posts.annotate(
        application_count=Count('applications'),
        pending_count=Count('applications', filter=Q(applications__status='PE')),
        accepted_count=Count('applications', filter=Q(applications__status='AC')),
        rejected_count=Count('applications', filter=Q(applications__status='RJ'))
    )
    
    # Check for updates if requested
    if request.GET.get('check_updates'):
        last_update = request.session.get('last_dashboard_update')
        current_update = applications.aggregate(
            max_updated=Max('updated_at'),
            count=Count('id')
        )
        
        has_updates = (
            not last_update or
            current_update['max_updated'] > last_update or
            current_update['count'] != request.session.get('last_application_count', 0)
        )
        
        if has_updates:
            request.session['last_dashboard_update'] = current_update['max_updated']
            request.session['last_application_count'] = current_update['count']
        
        return JsonResponse({
            'has_updates': has_updates,
            'last_update': current_update['max_updated'].isoformat() if current_update['max_updated'] else None,
            'application_count': current_update['count']
        })
    
    context = {
        'recruiter': recruiter,
        'job_posts': job_posts,
        'recent_applications': recent_applications,
        'active_jobs_count': job_posts.filter(status='OP').count(),
        'total_jobs_count': job_posts.count(),
        'application_stats': {
            'total': total_applications,
            'pending': pending_applications,
            'reviewing': reviewing_applications,
            'accepted': accepted_applications,
            'rejected': rejected_applications,
        },
        'jobs_with_stats': jobs_with_stats[:5]  # Top 5 jobs
    }
    
    return render(request, 'recruiters/dashboard.html', context)


@login_required
def recruiter_profile(request):
    """View recruiter profile"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Get job stats for the company profile page
    jobs = JobPost.objects.filter(posted_by=recruiter)
    total_jobs = jobs.count()
    active_jobs = jobs.filter(status='OP').count()
    total_applications = JobApplication.objects.filter(job__posted_by=recruiter).count()
    
    context = {
        'recruiter': recruiter,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'total_applications': total_applications
    }
    
    return render(request, 'recruiters/profile.html', context)


@login_required
def edit_profile(request):
    """Edit recruiter profile"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    if request.method == 'POST':
        # Get form data - both recruiter and company information
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone_number = request.POST.get('phone_number', '')
        company_name = request.POST.get('company_name')
        company_description = request.POST.get('company_description')
        
        # Validate required company fields
        if not company_name:
            messages.error(request, 'Company name is required')
            return redirect('recruiters:edit_profile')
            
        # Update user info (recruiter personal information)
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()
        
        # Update recruiter profile with both personal and company info
        recruiter.phone_number = phone_number
        recruiter.company_name = company_name
        recruiter.company_description = company_description
        
        recruiter.save()
        
        messages.success(request, 'Profile updated successfully')
        return redirect('recruiters:profile')
    
    context = {
        'recruiter': recruiter
    }
    
    return render(request, 'recruiters/edit_profile.html', context)


@login_required
def job_list(request):
    """View all jobs posted by the recruiter"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Get all jobs by this recruiter
    jobs = JobPost.objects.filter(posted_by=recruiter).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    
    context = {
        'jobs': jobs,
        'status_filter': status_filter,
        'status_choices': JobPost.STATUS_CHOICES,
    }
    
    return render(request, 'recruiters/job_list.html', context)


@login_required
def create_job(request):
    """Create a new job posting"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Get categories and locations for the form
    categories = JobCategory.objects.all()
    locations = JobLocation.objects.all()
    
    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        company_name = request.POST.get('company_name', recruiter.company_name)
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        requirements = request.POST.get('requirements')
        responsibilities = request.POST.get('responsibilities')
        location_id = request.POST.get('location')
        contract_type = request.POST.get('contract_type')
        status = request.POST.get('status', 'DR')  # Default to draft
        
        # Get salary range if provided
        salary_min = request.POST.get('salary_min')
        salary_max = request.POST.get('salary_max')
        
        # Get expiry date if provided (defaults to 30 days from now)
        expiry_date = request.POST.get('expiry_date')
        if not expiry_date:
            expiry_date = timezone.now() + timezone.timedelta(days=30)
        
        # Create or get location if needed
        if not location_id:
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            
            if city and country:
                location, created = JobLocation.objects.get_or_create(
                    city=city,
                    state=state,
                    country=country
                )
            else:
                location = None
        else:
            location = JobLocation.objects.get(id=location_id)
        
        # Get category if provided
        category = JobCategory.objects.get(id=category_id) if category_id else None
        
        # Create job post
        job = JobPost.objects.create(
            title=title,
            company_name=company_name,
            category=category,
            description=description,
            requirements=requirements,
            responsibilities=responsibilities,
            location=location,
            salary_min=salary_min if salary_min else None,
            salary_max=salary_max if salary_max else None,
            contract_type=contract_type,
            status=status,
            posted_by=recruiter,
            expiry_date=expiry_date
        )
        
        messages.success(request, 'Job posting created successfully')
        
        if status == 'DR':
            return redirect('recruiters:edit_job', job_id=job.id)
        else:
            return redirect('recruiters:job_list')
    
    context = {
        'recruiter': recruiter,
        'categories': categories,
        'locations': locations,
        'contract_types': JobPost.CONTRACT_TYPES,
    }
    
    return render(request, 'recruiters/create_job.html', context)


@login_required
def edit_job(request, job_id):
    """Edit an existing job posting"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Ensure the job belongs to this recruiter
    job = get_object_or_404(JobPost, id=job_id, posted_by=recruiter)
    
    # Get categories and locations for the form
    categories = JobCategory.objects.all()
    locations = JobLocation.objects.all()
    
    if request.method == 'POST':
        # Update job data
        job.title = request.POST.get('title')
        job.company_name = request.POST.get('company_name', recruiter.company_name)
        
        category_id = request.POST.get('category')
        job.category = JobCategory.objects.get(id=category_id) if category_id else None
        
        job.description = request.POST.get('description')
        job.requirements = request.POST.get('requirements')
        job.responsibilities = request.POST.get('responsibilities')
        
        location_id = request.POST.get('location')
        if location_id:
            job.location = JobLocation.objects.get(id=location_id)
        else:
            # Create new location if provided
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            
            if city and country:
                location, created = JobLocation.objects.get_or_create(
                    city=city,
                    state=state,
                    country=country
                )
                job.location = location
        
        # Update salary range
        job.salary_min = request.POST.get('salary_min') or None
        job.salary_max = request.POST.get('salary_max') or None
        
        job.contract_type = request.POST.get('contract_type')
        job.status = request.POST.get('status')
        
        # Update expiry date if provided
        expiry_date = request.POST.get('expiry_date')
        if expiry_date:
            job.expiry_date = expiry_date
        
        job.save()
        
        messages.success(request, 'Job posting updated successfully')
        return redirect('recruiters:job_list')
    
    context = {
        'job': job,
        'recruiter': recruiter,
        'categories': categories,
        'locations': locations,
        'contract_types': JobPost.CONTRACT_TYPES,
        'status_choices': JobPost.STATUS_CHOICES,
    }
    
    return render(request, 'recruiters/edit_job.html', context)


@login_required
def delete_job(request, job_id):
    """Delete a job posting"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Ensure the job belongs to this recruiter
    job = get_object_or_404(JobPost, id=job_id, posted_by=recruiter)
    
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job posting deleted successfully')
        return redirect('recruiters:job_list')
    
    context = {
        'job': job
    }
    
    return render(request, 'recruiters/confirm_delete_job.html', context)


@login_required
def job_applications(request, job_id):
    """View all applications for a specific job"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Ensure the job belongs to this recruiter
    job = get_object_or_404(JobPost, id=job_id, posted_by=recruiter)
    
    # Get all applications for this job
    applications = JobApplication.objects.filter(job=job).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    context = {
        'job': job,
        'applications': applications,
        'status_filter': status_filter,
        'status_choices': JobApplication.STATUS_CHOICES,
    }
    
    return render(request, 'recruiters/job_applications.html', context)


@login_required
def application_detail(request, application_id):
    """View details of a specific application"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Ensure the application belongs to a job posted by this recruiter
    application = get_object_or_404(JobApplication, id=application_id, job__posted_by=recruiter)
    
    # Get notes for this candidate
    notes = CandidateNote.objects.filter(
        recruiter=recruiter,
        candidate=application.candidate
    ).order_by('-created_at')
    
    context = {
        'application': application,
        'notes': notes,
    }
    
    return render(request, 'recruiters/application_detail.html', context)


@login_required
def update_application_status(request, application_id):
    """Update application status"""
    application = get_object_or_404(JobApplication, id=application_id)
    
    # Check if recruiter owns the job
    if application.job.posted_by != request.user.recruiter_profile:
        messages.error(request, 'You do not have permission to update this application.')
        return redirect('recruiters:dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(JobApplication.STATUS_CHOICES):
            old_status = application.status
            application.status = new_status
            application.save()
            
            # Create notification for candidate
            status_display = dict(JobApplication.STATUS_CHOICES)[new_status]
            Notification.objects.create(
                user=application.candidate.user,
                notification_type='AP',
                title='Application Status Updated',
                message=f'Your application for {application.job.title} has been {status_display.lower()}.'
            )
            
            messages.success(request, f'Application status updated to {status_display}')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('recruiters:application_detail', application_id=application.id)


@login_required
def candidate_notes(request, candidate_id):
    """View all notes for a specific candidate"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    # Ensure the candidate has applied to at least one of this recruiter's jobs
    if not JobApplication.objects.filter(candidate=candidate, job__posted_by=recruiter).exists():
        messages.error(request, 'You do not have access to this candidate')
        return redirect('recruiters:dashboard')
    
    # Get all notes for this candidate by this recruiter
    notes = CandidateNote.objects.filter(
        recruiter=recruiter,
        candidate=candidate
    ).order_by('-created_at')
    
    context = {
        'candidate': candidate,
        'notes': notes,
    }
    
    return render(request, 'recruiters/candidate_notes.html', context)


@login_required
def add_candidate_note(request, candidate_id):
    """Add a note for a specific candidate"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    # Ensure the candidate has applied to at least one of this recruiter's jobs
    if not JobApplication.objects.filter(candidate=candidate, job__posted_by=recruiter).exists():
        messages.error(request, 'You do not have access to this candidate')
        return redirect('recruiters:dashboard')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        
        # Create note
        note = CandidateNote.objects.create(
            recruiter=recruiter,
            candidate=candidate,
            content=content
        )
        
        messages.success(request, 'Note added successfully')
        
        # Redirect back to referring page if available
        referring_application = request.GET.get('application')
        if referring_application:
            return redirect('recruiters:application_detail', application_id=referring_application)
        else:
            return redirect('recruiters:candidate_notes', candidate_id=candidate.id)
    
    context = {
        'candidate': candidate,
    }
    
    return render(request, 'recruiters/add_note.html', context)


@login_required
def recruitment_stats(request):
    """View recruitment statistics and analytics"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Get all jobs by this recruiter
    jobs = JobPost.objects.filter(posted_by=recruiter)
    
    # Get application stats by job
    jobs_with_stats = jobs.annotate(
        application_count=Count('applications'),
        pending_count=Count('applications', filter=Q(applications__status='PE')),
        reviewing_count=Count('applications', filter=Q(applications__status='RV')),
        accepted_count=Count('applications', filter=Q(applications__status='AC')),
        rejected_count=Count('applications', filter=Q(applications__status='RJ')),
        waitlisted_count=Count('applications', filter=Q(applications__status='WL')),
    )
    
    # Calculate overall stats
    total_applications = sum(job.application_count for job in jobs_with_stats)
    total_pending = sum(job.pending_count for job in jobs_with_stats)
    total_reviewing = sum(job.reviewing_count for job in jobs_with_stats)
    total_accepted = sum(job.accepted_count for job in jobs_with_stats)
    total_rejected = sum(job.rejected_count for job in jobs_with_stats)
    total_waitlisted = sum(job.waitlisted_count for job in jobs_with_stats)
    
    context = {
        'recruiter': recruiter,
        'jobs_with_stats': jobs_with_stats,
        'overall_stats': {
            'total_applications': total_applications,
            'total_pending': total_pending,
            'total_reviewing': total_reviewing,
            'total_accepted': total_accepted,
            'total_rejected': total_rejected,
            'total_waitlisted': total_waitlisted,
        }
    }
    
    return render(request, 'recruiters/stats.html', context)


@login_required
def export_applications(request, job_id):
    """Export applications for a specific job in CSV format"""
    try:
        recruiter = Recruiter.objects.get(user=request.user)
    except Recruiter.DoesNotExist:
        messages.error(request, 'You do not have a recruiter profile')
        return redirect('jobs:home')
    
    # Ensure the job belongs to this recruiter
    job = get_object_or_404(JobPost, id=job_id, posted_by=recruiter)
    
    # Get all applications for this job
    applications = JobApplication.objects.filter(job=job).order_by('-created_at')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename=applications_{job.id}.csv'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'Candidate Name', 'Email', 'Phone', 'Status',
        'Applied On', 'Last Updated', 'Modified'
    ])
    
    # Write data
    for application in applications:
        candidate = application.candidate
        user = candidate.user
        writer.writerow([
            f"{user.first_name} {user.last_name}".strip() or user.username,
            user.email,
            candidate.phone_number or 'N/A',
            application.get_status_display(),
            application.created_at.strftime('%Y-%m-%d %H:%M'),
            application.updated_at.strftime('%Y-%m-%d %H:%M'),
            'Yes' if application.is_modified else 'No'
        ])
    
    return response
