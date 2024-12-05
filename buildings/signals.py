from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import NewUserProfile, BuildingWatchlist, PriceChange, WatchlistAlert, ApartmentWatchlist, Apartment

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    print("SIGNAL : CREATE USER PROFILE")
    if created:
        NewUserProfile.objects.create(user=instance)

def should_notify_user(user, apartment_type):
    """Helper function to check if user should be notified based on preferences"""

    print("should notify user? ")
    try:
        profile = user.profile
        preferences = profile.apartment_preferences
        if not preferences:
            print("no preference ")

            return True  # If no preferences set, notify about everything
        
        preferred_types = preferences.get('apartment_types', [])
        print("preference: ", preferred_types)
        print("returned: ", not preferred_types or apartment_type in preferred_types)
        return not preferred_types or apartment_type in preferred_types
    except NewUserProfile.DoesNotExist:
        return True  # If no profile exists, default to notifying

@receiver(post_save, sender=BuildingWatchlist)
def create_new_unit_alerts(sender, instance, created, **kwargs):
    if created:
        # Check for recent units that match user preferences
        print("Checking matching preference")
        
        recent_units = Apartment.objects.filter(
            building=instance.building,
            status='available',
            created_at__gte=timezone.now() - timedelta(days=1)
        ).select_related('building')
        
        print("Count of recent_units", recent_units)
        for unit in recent_units:
            # Check if this apartment type matches user preferences
            if should_notify_user(instance.user, unit.apartment_type):
                current_price = unit.price_history.order_by('-start_date').first()
                price_str = f" at ${current_price.price:,.2f}" if current_price else ""
                print(f'New {unit.apartment_type} unit {unit.unit_number} available{price_str} in {instance.building.name}.')
                WatchlistAlert.objects.create(
                    user=instance.user,
                    building=instance.building,
                    apartment=unit,
                    alert_type='new_unit',
                    message=f'New {unit.apartment_type} unit {unit.unit_number} available{price_str} in {instance.building.name}.'
                )

@receiver(post_save, sender=PriceChange)
def create_price_change_alerts(sender, instance, created, **kwargs):
    if created:
        # To avoid duplicates, we'll get all relevant watchlist items in one query
        affected_users = set()

        # Add users from apartment watchlist
        apartment_watchlist_items = ApartmentWatchlist.objects.filter(
            apartment=instance.apartment,
            notify_price_change=True
        ).select_related('user')
        
        # Add users from building watchlist
        building_watchlist_items = BuildingWatchlist.objects.filter(
            building=instance.apartment.building,
            notify_new_units=True
        ).select_related('user')
        
        price_change = ((instance.new_price - instance.old_price) / instance.old_price) * 100
        direction = "increased" if price_change > 0 else "decreased"
        
        message = (f"Price for {instance.apartment.building.name} "
                  f"Unit {instance.apartment.unit_number} has {direction} by "
                  f"{abs(price_change):.1f}% "
                  f"(from ${instance.old_price:,.2f} to ${instance.new_price:,.2f})")

        # Create alerts for unique users only
        for watchlist_item in apartment_watchlist_items:
            if watchlist_item.user.id not in affected_users:
                affected_users.add(watchlist_item.user.id)
                WatchlistAlert.objects.create(
                    user=watchlist_item.user,
                    apartment=instance.apartment,
                    alert_type='price_change',
                    message=message
                )
            
        # Create alerts for building watchlist users who haven't already been notified
        for watchlist_item in building_watchlist_items:
            if (watchlist_item.user.id not in affected_users and
                should_notify_user(watchlist_item.user, instance.apartment.apartment_type)):
                if not watchlist_item.max_price or instance.new_price <= watchlist_item.max_price:
                    affected_users.add(watchlist_item.user.id)
                    WatchlistAlert.objects.create(
                        user=watchlist_item.user,
                        building=instance.apartment.building,
                        apartment=instance.apartment,
                        alert_type='price_change',
                        message=message
                    )

@receiver(post_save, sender=Apartment)
def create_new_apartment_alerts(sender, instance, created, **kwargs):
    if created:
        print("SIGNAL: Apartment - create new apartment")
        building_watchlist_items = BuildingWatchlist.objects.filter(
            building=instance.building,
        ).select_related('user')
        print(building_watchlist_items)

        current_price = instance.price_history.order_by('-start_date').first()
        price_str = f" at ${current_price.price:,.2f}" if current_price else ""
        
        for watchlist_item in building_watchlist_items:
            if should_notify_user(watchlist_item.user, instance.apartment_type):
                print("NEED NOTIFY!")
                WatchlistAlert.objects.create(
                    user=watchlist_item.user,
                    building=instance.building,
                    apartment=instance,
                    alert_type='new_unit',
                    message=f'New {instance.apartment_type} unit {instance.unit_number} available{price_str} in {instance.building.name}.'
                )

@receiver(pre_save, sender=Apartment)
def create_status_change_alerts(sender, instance, **kwargs):
    try:
        old_instance = Apartment.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            # Track users who have been notified to prevent duplicates
            affected_users = set()
            
            # Handle apartment watchlist alerts
            apartment_watchlist_items = ApartmentWatchlist.objects.filter(
                apartment=instance,
                notify_availability_change=True
            ).select_related('user')
            
            # Handle building watchlist alerts
            building_watchlist_items = BuildingWatchlist.objects.filter(
                building=instance.building,
                notify_new_units=True
            ).select_related('user')
            
            message = f"Apartment {instance.unit_number} in {instance.building.name} is now {instance.status}."
            
            # Create alerts for apartment watchlist users
            for watchlist_item in apartment_watchlist_items:
                if watchlist_item.user.id not in affected_users:
                    affected_users.add(watchlist_item.user.id)
                    WatchlistAlert.objects.create(
                        user=watchlist_item.user,
                        apartment=instance,
                        alert_type='status_change',
                        message=message
                    )

            # Create alerts for building watchlist users who haven't been notified
            for watchlist_item in building_watchlist_items:
                if (watchlist_item.user.id not in affected_users and 
                    should_notify_user(watchlist_item.user, instance.apartment_type)):
                    affected_users.add(watchlist_item.user.id)
                    WatchlistAlert.objects.create(
                        user=watchlist_item.user,
                        apartment=instance,
                        alert_type='status_change',
                        message=message
                    )
                
    except Apartment.DoesNotExist:
        # This is a new apartment; no status change to process
        pass