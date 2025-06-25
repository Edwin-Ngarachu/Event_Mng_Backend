from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, role='booker', **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('booker', 'Event Booker'),
        ('poster', 'Event Poster'),
        ('admin', 'Admin'),
    )
    username = None  # Remove username field
    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='booker')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"
# backend_app/models.py

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateTimeField()
    poster = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='events')
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Add these two lines:
    location = models.CharField(max_length=255, blank=True, null=True)
    duration = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.title

class TicketType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    name = models.CharField(max_length=50)  # e.g. Regular, VIP, VVIP
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} - {self.event.title}"


class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    booked_at = models.DateTimeField(auto_now_add=True)
    ticket_number = models.CharField(max_length=100)