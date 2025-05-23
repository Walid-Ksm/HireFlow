from django.db import models
from django.utils import timezone
from recruiters.models import Recruiter


class JobCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Job Categories"
    
    def __str__(self):
        return self.name


class JobLocation(models.Model):
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.city}, {self.country}"


class JobPost(models.Model):
    CONTRACT_TYPES = (
        ('FT', 'Full Time'),
        ('PT', 'Part Time'),
        ('CT', 'Contract'),
        ('IN', 'Internship'),
        ('FR', 'Freelance'),
    )
    
    STATUS_CHOICES = (
        ('DR', 'Draft'),
        ('OP', 'Open'),
        ('CL', 'Closed'),
    )
    
    title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True)
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField()
    location = models.ForeignKey(JobLocation, on_delete=models.SET_NULL, null=True)
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    contract_type = models.CharField(max_length=2, choices=CONTRACT_TYPES, default='FT')
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='DR')
    
    posted_by = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name='job_posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expiry_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.title
    
    def is_expired(self):
        return timezone.now() > self.expiry_date
    
    class Meta:
        ordering = ['-created_at']
