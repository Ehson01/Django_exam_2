from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(max_length=100)

    def __str__(self):
        return self.name


class Job(models.Model):
    
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    salary = models.DecimalField(max_digits=8, decimal_places=2)
    location = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='jobs')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    
    def __str__(self):
        return self.title


from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(max_length=100)

    class Meta:
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name


class Job(models.Model):
    EMPLOYMENT_CHOICES = [
        ('full_time', 'full_time'),
        ('part_time', 'part_time'),
        ('remote', 'remote'),
        ('contract', 'contract'),
        ('internship', 'internship'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    salary = models.DecimalField(max_digits=8, decimal_places=2)
    location = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=100, choices=EMPLOYMENT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='jobs')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('accepted', 'accepted'),
        ('rejected', 'rejected'),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['job', 'user'], name='unique_application_per_user'),
        ]

    def __str__(self):
        return f'{self.user.username}  {self.job.title}'
