from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.db.models import Q, Max, Count
from django.http import JsonResponse
from django.urls import reverse

from .models import Candidate, JobApplication, EmailVerification
from jobs.models import JobPost


def candidate_register(request):
    """Register a new candidate account"""
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validate form data
        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return redirect('candidates:register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('candidates:register')
        
        # Check if email is already used by a candidate
        existing_user_with_email = User.objects.filter(email=email).first()
        if existing_user_with_email and Candidate.objects.filter(user=existing_user_with_email).exists():
            messages.error(request, 'A candidate account with this email already exists')
            return redirect('candidates:register')
        
        # Create user and candidate profile
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            candidate = Candidate.objects.create(user=user)
            
            # Create email verification token
            token = get_random_string(length=64)
            verification = EmailVerification.objects.create(user=user, token=token)
            
            # Send verification email
            verification_url = f"{request.scheme}://{request.get_host()}/candidates/verify-email/{token}/"
            send_mail(
                'Verify Your Email',
                f'Please click the link to verify your email: {verification_url}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            # Log in the user
            login(request, user)
            messages.success(request, 'Account created successfully. Please verify your email.')
            return redirect('candidates:dashboard')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('candidates:register')
    
    return render(request, 'candidates/register.html')


def verify_email(request, token):
    """Verify candidate's email using token"""
    try:
        verification = EmailVerification.objects.get(token=token, is_used=False)
        if verification.is_expired():
            messages.error(request, 'Verification link has expired. Please request a new one.')
            return redirect('candidates:profile')
        
        candidate = verification.candidate
        candidate.is_email_verified = True
        candidate.save()
        
        verification.is_used = True
        verification.save()
        
        messages.success(request, 'Email verified successfully!')
        return redirect('candidates:dashboard')
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('candidates:profile')


def resend_verification(request):
    """Resend email verification link"""
    if not request.user.is_authenticated:
        return redirect('candidates:login')
    
    try:
        candidate = Candidate.objects.get(user=request.user)
        if candidate.is_email_verified:
            messages.info(request, 'Your email is already verified.')
            return redirect('candidates:dashboard')
        
        # Create new verification token
        verification = EmailVerification.objects.create(candidate=candidate)
        
        # Send verification email
        subject = 'Verify your email - Job Portal'
        verification_url = request.build_absolute_uri(
            reverse('candidates:verify_email', args=[verification.token])
        )
        message = f'Please click the following link to verify your email: {verification_url}'
        candidate.user.email_user(subject, message)
        
        messages.success(request, 'Verification email sent. Please check your inbox.')
    except Candidate.DoesNotExist:
        messages.error(request, 'Candidate profile not found.')
    
    return redirect('candidates:profile')


def candidate_login(request):
    """Log in an existing candidate"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user has a candidate profile
            try:
                candidate = Candidate.objects.get(user=user)
                login(request, user)
                messages.success(request, 'Logged in successfully')
                return redirect('candidates:dashboard')
            except Candidate.DoesNotExist:
                messages.error(request, 'This account is not a candidate account')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'candidates/login.html')


def candidate_logout(request):
    """Log out the candidate"""
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('jobs:home')


@login_required
def candidate_dashboard(request):
    """Show candidate dashboard with applications and stats"""
    try:
        candidate = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        messages.error(request, 'You do not have a candidate profile')
        return redirect('jobs:home')
    
    # Get candidate's applications
    applications = JobApplication.objects.filter(candidate=candidate).order_by('-created_at')
    
    # Count applications by status
    pending_count = applications.filter(status='PE').count()
    accepted_count = applications.filter(status='AC').count()
    rejected_count = applications.filter(status='RJ').count()
    reviewing_count = applications.filter(status='RV').count()
    
    # Get recent applications
    recent_applications = applications[:5]
    
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
        'candidate': candidate,
        'applications': applications,
        'recent_applications': recent_applications,
        'application_counts': {
            'total': applications.count(),
            'pending': pending_count,
            'accepted': accepted_count,
            'rejected': rejected_count,
            'reviewing': reviewing_count,
        }
    }
    
    return render(request, 'candidates/dashboard.html', context)


@login_required
def candidate_profile(request):
    """View candidate profile"""
    try:
        candidate = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        messages.error(request, 'You do not have a candidate profile')
        return redirect('jobs:home')
    
    context = {
        'candidate': candidate
    }
    
    return render(request, 'candidates/profile.html', context)


@login_required
def edit_profile(request):
    """Edit candidate profile"""
    try:
        candidate = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        messages.error(request, 'You do not have a candidate profile')
        return redirect('jobs:home')
    
    if request.method == 'POST':
        # Update user info
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')
        request.user.save()
        
        # Update candidate profile
        candidate.phone_number = request.POST.get('phone_number')
        candidate.address = request.POST.get('address')
        candidate.skills = request.POST.get('skills')
        candidate.education = request.POST.get('education')
        candidate.experience = request.POST.get('experience')
        
        # Handle URL fields - convert empty strings to None
        portfolio_url = request.POST.get('portfolio_url', '').strip()
        linkedin_profile = request.POST.get('linkedin_profile', '').strip()
        
        # Only save URLs if they're valid
        try:
            candidate.portfolio_url = None if not portfolio_url else portfolio_url
        except:
            # If URL validation fails, set to None
            candidate.portfolio_url = None
            messages.warning(request, 'Invalid portfolio URL format - it was not saved')
            
        try:
            candidate.linkedin_profile = None if not linkedin_profile else linkedin_profile
        except:
            # If URL validation fails, set to None
            candidate.linkedin_profile = None
            messages.warning(request, 'Invalid LinkedIn URL format - it was not saved')
        
        # Handle resume upload
        if 'resume' in request.FILES:
            candidate.resume = request.FILES['resume']
        
        # Handle profile image (now storing just the filename)
        if 'profile_image' in request.FILES:
            # Store the filename instead of the file itself
            candidate.profile_image = request.FILES['profile_image'].name
        
        try:
            candidate.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('candidates:profile')
        except Exception as e:
            messages.error(request, f'Error saving profile: {str(e)}')
    
    context = {
        'candidate': candidate
    }
    
    return render(request, 'candidates/edit_profile.html', context)


@login_required
def application_list(request):
    """View all applications by the candidate"""
    try:
        candidate = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        messages.error(request, 'You do not have a candidate profile')
        return redirect('jobs:home')
    
    # Get all applications
    applications = JobApplication.objects.filter(candidate=candidate).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    context = {
        'applications': applications,
        'status_filter': status_filter,
        'status_choices': JobApplication.STATUS_CHOICES,
    }
    
    return render(request, 'candidates/application_list.html', context)


@login_required
def apply_job(request, job_id):
    """Apply for a job"""
    try:
        candidate = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        messages.error(request, 'You do not have a candidate profile')
        return redirect('jobs:home')
    
    job = get_object_or_404(JobPost, id=job_id)
    
    # Check if the job is open and not expired
    if job.status != 'OP' or job.is_expired():
        messages.error(request, 'This job is not accepting applications')
        return redirect('jobs:job_detail', job_id=job_id)
    
    # Check if already applied
    if JobApplication.objects.filter(candidate=candidate, job=job).exists():
        messages.info(request, 'You have already applied for this job')
        return redirect('jobs:job_detail', job_id=job_id)
    
    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter')
        
        # Handle resume upload
        if 'resume' in request.FILES:
            resume = request.FILES['resume']
        else:
            # Use existing resume if available
            resume = candidate.resume
            if not resume:
                messages.error(request, 'Please upload a resume')
                return redirect('candidates:apply_job', job_id=job_id)
        
        # Create application
        application = JobApplication.objects.create(
            candidate=candidate,
            job=job,
            cover_letter=cover_letter,
            resume=resume,
            status='PE'  # Pending status
        )
        
        messages.success(request, 'Application submitted successfully')
        return redirect('candidates:application_detail', application_id=application.id)
    
    context = {
        'job': job,
        'candidate': candidate
    }
    
    return render(request, 'candidates/apply_job.html', context)


@login_required
def application_detail(request, application_id):
    """View details of a specific application"""
    try:
        candidate = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        messages.error(request, 'You do not have a candidate profile')
        return redirect('jobs:home')
    
    application = get_object_or_404(JobApplication, id=application_id, candidate=candidate)
    
    context = {
        'application': application
    }
    
    return render(request, 'candidates/application_detail.html', context)


@login_required
def edit_application(request, application_id):
    """Edit an existing application"""
    try:
        candidate = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        messages.error(request, 'You do not have a candidate profile')
        return redirect('jobs:home')
    
    application = get_object_or_404(JobApplication, id=application_id, candidate=candidate)
    
    # Only allow editing pending applications
    if application.status != 'PE':
        messages.error(request, 'You can only edit pending applications')
        return redirect('candidates:application_detail', application_id=application.id)
    
    if request.method == 'POST':
        application.cover_letter = request.POST.get('cover_letter')
        
        # Handle resume upload
        if 'resume' in request.FILES:
            application.resume = request.FILES['resume']
        
        application.is_modified = True
        application.save()
        
        messages.success(request, 'Application updated successfully')
        return redirect('candidates:application_detail', application_id=application.id)
    
    context = {
        'application': application
    }
    
    return render(request, 'candidates/edit_application.html', context)


@login_required
def delete_application(request, application_id):
    """Delete an application"""
    try:
        candidate = Candidate.objects.get(user=request.user)
    except Candidate.DoesNotExist:
        messages.error(request, 'You do not have a candidate profile')
        return redirect('jobs:home')
    
    application = get_object_or_404(JobApplication, id=application_id, candidate=candidate)
    
    # Only allow deleting pending applications
    if application.status != 'PE':
        messages.error(request, 'You can only delete pending applications')
        return redirect('candidates:application_detail', application_id=application.id)
    
    if request.method == 'POST':
        application.delete()
        messages.success(request, 'Application deleted successfully')
        return redirect('candidates:applications')
    
    context = {
        'application': application
    }
    
    return render(request, 'candidates/confirm_delete.html', context)
