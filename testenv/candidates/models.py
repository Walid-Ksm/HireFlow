from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver
from jobs.models import JobPost


class OptionalURLField(models.URLField):
    """A URL field that allows empty values."""
    
    def to_python(self, value):
        if value in self.empty_values:
            return None
        return super().to_python(value)


class Candidate(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    profile_image = models.CharField(max_length=255, blank=True, null=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    experience = models.TextField(blank=True, null=True)
    portfolio_url = OptionalURLField(blank=True, null=True)
    linkedin_profile = OptionalURLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_email_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username


class JobApplication(models.Model):
    STATUS_CHOICES = (
        ('PE', 'Pending'),
        ('RV', 'Reviewing'),
        ('AC', 'Accepted'),
        ('RJ', 'Rejected'),
        ('WL', 'Waitlisted'),
    )
    
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField()
    resume = models.FileField(upload_to='application_resumes/')
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='PE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_modified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.candidate} - {self.job.title}"
    
    class Meta:
        unique_together = ('candidate', 'job')
        ordering = ['-created_at']


class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Verification for {self.user.username}"
    
    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(days=2)


class Notification(models.Model):
    """Model for user notifications"""
    NOTIFICATION_TYPES = (
        ('AP', 'Application Status'),
        ('EM', 'Email Verification'),
        ('SY', 'System'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='candidate_notifications')
    notification_type = models.CharField(max_length=2, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.created_at}"


# This patch for User model makes email not unique across all users
@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    # Setting _email_being_validated to True will skip the uniqueness check
    instance._email_being_validated = False
