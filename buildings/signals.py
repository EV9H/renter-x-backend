from django.db.models.signals import post_save
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

@receiver(post_save, sender=BuildingWatchlist)
def create_new_unit_alerts(sender, instance, created, **kwargs):
    print("SIGNAL : create_new_unit_alerts")

    if created and instance.unit_type_preference:
        print("SIGNAL : create_new_unit_alerts 02")

        recent_units = Apartment.objects.filter(
            building=instance.building,
            apartment_type=instance.unit_type_preference,
            status='available',
            created_at__gte=timezone.now() - timedelta(days=1)
        ).select_related('building')
        
        for unit in recent_units:
            current_price = unit.price_history.order_by('-start_date').first()
            price_str = f" at ${current_price.price:,.2f}" if current_price else ""
            
            WatchlistAlert.objects.create(
                user=instance.user,
                building=instance.building,
                apartment=unit,
                alert_type='new_unit',
                message=f'New {unit.apartment_type} unit {unit.unit_number} available{price_str} in {instance.building.name}.'
            )

@receiver(post_save, sender=PriceChange)
def create_price_change_alerts(sender, instance, created, **kwargs):
    print("SIGNAL : create_price_change_alerts")
    if created:
        print("SIGNAL : create_price_change_alerts 02 ")
        
        # Get all watchlist items for this apartment
        apartment_watchlist_items = ApartmentWatchlist.objects.filter(
            apartment=instance.apartment,
            notify_price_change=True
        ).select_related('user')
        
        # Get all building watchlist items that match this apartment's type
        building_watchlist_items = BuildingWatchlist.objects.filter(
            building=instance.apartment.building,
            unit_type_preference=instance.apartment.apartment_type,
            notify_new_units=True
        ).select_related('user')
        
        # Calculate price change percentage
        price_change = ((instance.new_price - instance.old_price) / instance.old_price) * 100
        direction = "increased" if price_change > 0 else "decreased"
        
        message = (f"Price for {instance.apartment.building.name} "
                  f"Unit {instance.apartment.unit_number} has {direction} by "
                  f"{abs(price_change):.1f}% "
                  f"(from ${instance.old_price:,.2f} to ${instance.new_price:,.2f})")

        # Create alerts for apartment watchlist
        for watchlist_item in apartment_watchlist_items:
            WatchlistAlert.objects.create(
                user=watchlist_item.user,
                apartment=instance.apartment,
                alert_type='price_change',
                message=message
            )
            
        # Create alerts for building watchlist if price is under max_price
        for watchlist_item in building_watchlist_items:
            if not watchlist_item.max_price or instance.new_price <= watchlist_item.max_price:
                WatchlistAlert.objects.create(
                    user=watchlist_item.user,
                    building=instance.apartment.building,
                    apartment=instance.apartment,
                    alert_type='price_change',
                    message=message
                )

@receiver(post_save, sender=Apartment)
def create_new_apartment_alerts(sender, instance, created, **kwargs):
    print("NEW APARTMENMT")
    if created:
        print("NEW APARTMENMT -> CREATED")

        building_watchlist_items = BuildingWatchlist.objects.filter(
            building=instance.building,
        ).select_related('user')
        print(building_watchlist_items)
        current_price = instance.price_history.order_by('-start_date').first()
        price_str = f" at ${current_price.price:,.2f}" if current_price else ""
        
        for watchlist_item in building_watchlist_items:
            WatchlistAlert.objects.create(
                user=watchlist_item.user,
                building=instance.building,
                apartment=instance,
                alert_type='new_unit',
                message=f'New {instance.apartment_type} unit {instance.unit_number} available{price_str} in {instance.building.name}.'
            )

@receiver(post_save, sender=Apartment)
def create_status_change_alerts(sender, instance, **kwargs):
    try:
        old_instance = Apartment.objects.get(pk=instance.pk)
        print("oldinstance", old_instance.status)

    except Apartment.DoesNotExist:
        # This is a new apartment; no status change to process
        return
    print("STATUS CHANGE!")
    print("new instance", instance.status)
    if old_instance.status != instance.status:
        print("STATUS CHANGE! 02")
        if instance.status == 'unavailable':
            watchlist_items = ApartmentWatchlist.objects.filter(
                apartment=instance,
            ).select_related('user')
            message = f"Apartment {instance.unit_number} in {instance.building.name} is now unavailable."
            for watchlist_item in watchlist_items:
                WatchlistAlert.objects.create(
                    user=watchlist_item.user,
                    apartment=instance,
                    alert_type='status_change',
                    message=message
                )
