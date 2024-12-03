from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User, AbstractUser, BaseUserManager, UserManager
from django.utils.translation import gettext_lazy as _

class Building(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=500)
    postal_code = models.CharField(max_length=10)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    website = models.URLField(max_length=500)
    phone = models.CharField(max_length=20, null=True, blank=True)
    year_built = models.IntegerField(null=True, blank=True)
    
    # Amenities as a JSON field for flexibility
    amenities = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.address}"

    class Meta:
        indexes = [
            models.Index(fields=['postal_code']),
            models.Index(fields=['city', 'state']),
        ]


class Apartment(models.Model):
    class ApartmentStatus(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        PENDING = 'pending', 'Pending'
        LEASED = 'leased', 'Leased'
        UNAVAILABLE = 'unavailable', 'Unavailable'

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='apartments')
    unit_number = models.CharField(max_length=20)
    floor = models.IntegerField()
    bedrooms = models.DecimalField(max_digits=3, decimal_places=1)  # Allow for studios (0) and half-rooms
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1)  # Allow for half-baths
    area_sqft = models.IntegerField()
    apartment_type = models.CharField(max_length=50)  # e.g., "Studio", "1B1B", "2B2B"
    status = models.CharField(
        max_length=20,
        choices=ApartmentStatus.choices,
        default=ApartmentStatus.AVAILABLE
    )
    
    # Optional fields
    features = models.JSONField(default=dict)  # Specific features of this unit
    # floor_plan_image = models.ImageField(upload_to='floor_plans/', null=True, blank=True)
    # virtual_tour_url = models.URLField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Unit {self.unit_number} - {self.building.name}"

    class Meta:
        unique_together = ['building', 'unit_number']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['bedrooms']),
            models.Index(fields=['area_sqft']),
        ]


class ApartmentPrice(models.Model):
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    lease_term_months = models.IntegerField()
    is_special_offer = models.BooleanField(default=False)
    special_offer_details = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['start_date']),
            models.Index(fields=['price']),
        ]


class ScrapingSource(models.Model):
    name = models.CharField(max_length=100)
    base_url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)
    scraping_frequency_hours = models.IntegerField(default=24)
    
    # Store scraping configuration as JSON for flexibility
    scraping_config = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ScrapingRun(models.Model):
    class RunStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    source = models.ForeignKey(ScrapingSource, on_delete=models.CASCADE, related_name='runs')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=RunStatus.choices,
        default=RunStatus.PENDING
    )
    items_processed = models.IntegerField(default=0)
    items_created = models.IntegerField(default=0)
    items_updated = models.IntegerField(default=0)
    items_errored = models.IntegerField(default=0)
    error_log = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['status']),
        ]


class PriceChange(models.Model):
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name='price_changes')
    old_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    detected_at = models.DateTimeField(auto_now_add=True)
    scraping_run = models.ForeignKey(ScrapingRun, on_delete=models.CASCADE, related_name='price_changes')
    

    class Meta:
        indexes = [
            models.Index(fields=['detected_at']),
        ]


# class CustomUserManager(BaseUserManager):
#     def create_user(self, email, password=None, **extra_fields):
#         if not email:
#             raise ValueError('The Email field must be set')
#         email = self.normalize_email(email)
#         user = self.model(email=email, **extra_fields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user

#     def create_superuser(self, email, password=None, **extra_fields):
#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         return self.create_user(email, password, **extra_fields)

# class CustomUser(AbstractUser):
#     username = None
#     email = models.EmailField(_('email address'), unique=True)
    
#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = []

#     objects = CustomUserManager()

#     def __str__(self):
#         return self.email
class NewUserManager(UserManager):

    def create_user(self,email,name,password=None):
        """Create a new user profile"""
        if not email:
            raise ValueError('User must have an email address')
        
        email = self.normalize_email(email) 
        user = self.model(email=email,name=name) 
        user.set_password(password)
        user.save(using=self.db)
        return user

class NewUserProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='profile'
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    preferred_contact_method = models.CharField(
        max_length=10,
        choices=[('email', 'Email'), ('phone', 'Phone')],
        default='email'
    )
    notification_preferences = models.JSONField(default=dict)
    saved_searches = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.email}"

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['phone_number']),
        ]
    


class ApartmentWatchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='apartment_watchlist')
    apartment = models.ForeignKey('Apartment', on_delete=models.CASCADE)
    notify_price_change = models.BooleanField(default=True)
    notify_availability_change = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_notified = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'apartment']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['last_notified']),
        ]

class BuildingWatchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='building_watchlist')
    building = models.ForeignKey('Building', on_delete=models.CASCADE)
    notify_new_units = models.BooleanField(default=True)
    unit_type_preference = models.CharField(max_length=50, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_notified = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'building']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['last_notified']),
            models.Index(fields=['unit_type_preference']),
        ]

class WatchlistAlert(models.Model):
    ALERT_TYPES = (
        ('new_unit', 'New Unit Available'),
        ('price_change', 'Price Change'),
        ('status_change', 'Status Change'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist_alerts')
    building = models.ForeignKey('Building', on_delete=models.CASCADE, null=True, blank=True)
    apartment = models.ForeignKey('Apartment', on_delete=models.CASCADE, null=True, blank=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['read']),
            models.Index(fields=['alert_type']),
            models.Index(fields=['user', 'read']),
        ]