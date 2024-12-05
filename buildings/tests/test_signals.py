# buildings/tests/test_signals.py
import pytest
from django.contrib.auth.models import User
from buildings.models import *
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
@pytest.mark.django_db
class TestSignals:
    def test_user_profile_creation(self):
        """Test that a NewUserProfile is created when a User is created"""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        assert NewUserProfile.objects.filter(user=user).exists()
        profile = NewUserProfile.objects.get(user=user)
        assert profile.preferred_contact_method == 'email'

    def test_new_apartment_alert(self, django_user_model):
        """Test alert creation when a new apartment is added"""
        # Setup
        user = django_user_model.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        region = Region.objects.create(
            name="Test Region",
            borough="MAN",
            neighborhood="LES"
        )
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY",
            region=region
        )
        
        # Create building watchlist
        BuildingWatchlist.objects.create(
            user=user,
            building=building,
            notify_new_units=True,
            unit_type_preference="1B1B"
        )
        
        # Create new apartment
        apartment = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=800,
            apartment_type="1B1B",
            status="available"
        )
        
        # Check if alert was created
        alert = WatchlistAlert.objects.filter(
            user=user,
            building=building,
            apartment=apartment,
            alert_type='new_unit'
        ).first()
        
        assert alert is not None
        assert "1B1B unit 101" in alert.message
        
    def test_price_change_alert(self, django_user_model):
        """Test alert creation when apartment price changes"""
        # Setup
        user = django_user_model.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        apartment = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=800,
            apartment_type="1B1B",
            status="available"
        )
        
        # Create watchlist entry
        watchlist = ApartmentWatchlist.objects.create(
            user=user,
            apartment=apartment,
            notify_price_change=True
        )
        
        # Create scraping source and run
        source = ScrapingSource.objects.create(
            name="Test Source",
            base_url="http://test.com",
            is_active=True
        )
        
        scraping_run = ScrapingRun.objects.create(
            source=source,
            start_time=timezone.now(),
            status='completed'
        )
        
        # Create price change record
        price_change = PriceChange.objects.create(
            apartment=apartment,
            old_price=Decimal("3000"),
            new_price=Decimal("3500"),
            scraping_run=scraping_run
        )
        
        # Check if alert was created
        alert = WatchlistAlert.objects.filter(
            user=user,
            apartment=apartment,
            alert_type='price_change'
        ).first()
        
        assert alert is not None
        assert "increased" in alert.message
        assert "3,000" in alert.message
        assert "3,500" in alert.message

    def test_apartment_status_change_alert(self, django_user_model):
        """Test alert creation when apartment status changes"""
        # Setup
        user = django_user_model.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        apartment = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=800,
            apartment_type="1B1B",
            status="available"
        )
        
        # Create watchlist entry
        ApartmentWatchlist.objects.create(
            user=user,
            apartment=apartment,
            notify_availability_change=True
        )
        
        # Change status
        apartment.status = "pending"
        apartment.save()
        
        # Check if alert was created
        alert = WatchlistAlert.objects.filter(
            user=user,
            apartment=apartment,
            alert_type='status_change'
        ).first()
        
        assert alert is not None
        assert "pending" in alert.message

    def test_should_notify_user_preferences(self, django_user_model):
        """Test notification filtering based on user preferences"""
        user = django_user_model.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        profile = NewUserProfile.objects.get(user=user)
        profile.apartment_preferences = {
            'apartment_types': ['1B1B', '2B2B']
        }
        profile.save()
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        # Create building watchlist
        watchlist = BuildingWatchlist.objects.create(
            user=user,
            building=building,
            notify_new_units=True
        )
        
        # Create apartments of different types
        apt_1b = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=800,
            apartment_type="1B1B",
            status="available"
        )
        
        apt_studio = Apartment.objects.create(
            building=building,
            unit_number="102",
            floor=1,
            bedrooms=Decimal("0"),
            bathrooms=Decimal("1"),
            area_sqft=500,
            apartment_type="Studio",
            status="available"
        )
        
        # Check alerts were created only for preferred types
        alerts = WatchlistAlert.objects.filter(
            user=user,
            building=building
        )
        
        assert alerts.count() == 1
        assert alerts.filter(apartment=apt_1b).exists()
        assert not alerts.filter(apartment=apt_studio).exists()

@pytest.mark.django_db
class TestWatchlistIntegration:
    def test_watchlist_cascade_deletion(self, django_user_model):
        """Test proper cleanup when a user is deleted"""
        user = django_user_model.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        apartment = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=800,
            status="available"
        )
        
        # Store user ID for later querying
        user_id = user.id
        
        # Create watchlist entries
        BuildingWatchlist.objects.create(
            user=user,
            building=building
        )
        
        ApartmentWatchlist.objects.create(
            user=user,
            apartment=apartment
        )
        
        WatchlistAlert.objects.create(
            user=user,
            building=building,
            alert_type='new_unit',
            message='Test alert'
        )
        
        # Verify objects exist
        assert BuildingWatchlist.objects.filter(user_id=user_id).exists()
        assert ApartmentWatchlist.objects.filter(user_id=user_id).exists()
        assert WatchlistAlert.objects.filter(user_id=user_id).exists()
        
        # Delete user
        user.delete()
        
        # Check using ID instead of user instance
        assert not BuildingWatchlist.objects.filter(user_id=user_id).exists()
        assert not ApartmentWatchlist.objects.filter(user_id=user_id).exists()
        assert not WatchlistAlert.objects.filter(user_id=user_id).exists()

    def test_multiple_watchlist_notifications(self, django_user_model):
        """Test handling of multiple watchlist notifications for the same event"""
        user = django_user_model.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        apartment = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=800,
            status="available"
        )
        
        # Clear any existing alerts
        WatchlistAlert.objects.all().delete()
        
        # Create both types of watchlist entries
        BuildingWatchlist.objects.create(
            user=user,
            building=building,
            notify_new_units=True
        )
        
        ApartmentWatchlist.objects.create(
            user=user,
            apartment=apartment,
            notify_price_change=True
        )
        
        # Create scraping source and run
        source = ScrapingSource.objects.create(
            name="Test Source",
            base_url="http://test.com",
            is_active=True
        )
        
        scraping_run = ScrapingRun.objects.create(
            source=source,
            start_time=timezone.now(),
            status='completed'
        )
        
        # Create price change
        price_change = PriceChange.objects.create(
            apartment=apartment,
            old_price=Decimal("3000"),
            new_price=Decimal("3500"),
            scraping_run=scraping_run,
            detected_at=timezone.now()
        )

        # Check alerts - should only be one despite having both watchlist entries
        alerts = WatchlistAlert.objects.filter(
            user=user,
            apartment=apartment,
            alert_type='price_change'
        )
        
        # Print debug information if test fails
        if alerts.count() != 1:
            print(f"\nFound {alerts.count()} alerts:")
            for alert in alerts:
                print(f"Alert ID: {alert.id}, User: {alert.user.email}, Message: {alert.message}")
        
        assert alerts.count() == 1, "Expected exactly one alert per price change"
        alert = alerts.first()
        assert "3,000" in alert.message
        assert "3,500" in alert.message


@pytest.mark.django_db
class TestWatchlistAlerts:
    def test_status_change_notification(self, django_user_model):
        """Test alerts are created when apartment status changes"""
        # Setup
        user = django_user_model.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        apartment = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=800,
            apartment_type="1B1B",
            status="available"
        )
        
        # Create both types of watchlist entries
        BuildingWatchlist.objects.create(
            user=user,
            building=building,
            notify_new_units=True
        )
        
        ApartmentWatchlist.objects.create(
            user=user,
            apartment=apartment,
            notify_availability_change=True
        )
        
        # Clear any existing alerts
        WatchlistAlert.objects.all().delete()
        
        # Change status
        apartment.status = "pending"
        apartment.save()
        
        # Verify alerts
        alerts = WatchlistAlert.objects.filter(
            user=user,
            apartment=apartment,
            alert_type='status_change'
        )
        
        assert alerts.count() == 1, "Should receive exactly one status change alert"
        alert = alerts.first()
        assert "pending" in alert.message
        assert apartment.unit_number in alert.message

    def test_new_unit_alert_preferences(self, django_user_model):
        """Test new unit alerts respect user preferences"""
        # Setup
        user = django_user_model.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Set user preferences
        profile = NewUserProfile.objects.get(user=user)
        profile.apartment_preferences = {
            'apartment_types': ['1B1B', '2B2B']  # Only interested in 1 and 2 bedrooms
        }
        profile.save()
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        # Create building watchlist
        BuildingWatchlist.objects.create(
            user=user,
            building=building,
            notify_new_units=True
        )
        
        # Clear existing alerts
        WatchlistAlert.objects.all().delete()
        
        # Create apartments of different types
        studio_apt = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("0"),
            bathrooms=Decimal("1"),
            area_sqft=500,
            apartment_type="Studio",
            status="available"
        )
        
        one_bed_apt = Apartment.objects.create(
            building=building,
            unit_number="102",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=700,
            apartment_type="1B1B",
            status="available"
        )
        
        # Check alerts
        alerts = WatchlistAlert.objects.filter(
            user=user,
            alert_type='new_unit'
        )
        
        assert alerts.count() == 1, "Should only receive alert for preferred unit type"
        assert all(alert.apartment.apartment_type in ['1B1B', '2B2B'] for alert in alerts)

    def test_multiple_users_new_unit_alert(self, django_user_model):
        """Test new unit alerts are created for all watching users"""
        # Create users
        user1 = django_user_model.objects.create(username="user1", email="user1@test.com")
        user2 = django_user_model.objects.create(username="user2", email="user2@test.com")
        user3 = django_user_model.objects.create(username="user3", email="user3@test.com")
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        # Create watchlist entries for users 1 and 2, but not 3
        BuildingWatchlist.objects.create(user=user1, building=building, notify_new_units=True)
        BuildingWatchlist.objects.create(user=user2, building=building, notify_new_units=True)
        
        # Clear existing alerts
        WatchlistAlert.objects.all().delete()
        
        # Create new apartment
        apartment = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("2"),
            bathrooms=Decimal("2"),
            area_sqft=1000,
            apartment_type="2B2B",
            status="available"
        )
        
        # Verify alerts
        user1_alerts = WatchlistAlert.objects.filter(user=user1, alert_type='new_unit')
        user2_alerts = WatchlistAlert.objects.filter(user=user2, alert_type='new_unit')
        user3_alerts = WatchlistAlert.objects.filter(user=user3, alert_type='new_unit')
        
        assert user1_alerts.count() == 1, "User 1 should receive an alert"
        assert user2_alerts.count() == 1, "User 2 should receive an alert"
        assert user3_alerts.count() == 0, "User 3 should not receive an alert"

    def test_price_and_status_change_combination(self, django_user_model):
        """Test handling of simultaneous price and status changes"""
        user = django_user_model.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="10001",
            city="New York",
            state="NY"
        )
        
        apartment = Apartment.objects.create(
            building=building,
            unit_number="101",
            floor=1,
            bedrooms=Decimal("1"),
            bathrooms=Decimal("1"),
            area_sqft=800,
            apartment_type="1B1B",
            status="available"
        )
        
        # Create watchlist entries
        ApartmentWatchlist.objects.create(
            user=user,
            apartment=apartment,
            notify_price_change=True,
            notify_availability_change=True
        )
        
        # Clear existing alerts
        WatchlistAlert.objects.all().delete()
        
        # Create scraping source and run
        source = ScrapingSource.objects.create(
            name="Test Source",
            base_url="http://test.com",
            is_active=True
        )
        
        scraping_run = ScrapingRun.objects.create(
            source=source,
            start_time=timezone.now(),
            status='completed'
        )
        
        # Create price change and status change
        PriceChange.objects.create(
            apartment=apartment,
            old_price=Decimal("3000"),
            new_price=Decimal("3500"),
            scraping_run=scraping_run
        )
        
        apartment.status = "pending"
        apartment.save()
        
        # Check alerts
        alerts = WatchlistAlert.objects.filter(
            user=user,
            apartment=apartment
        ).order_by('created_at')
        
        assert alerts.count() == 2, "Should receive separate alerts for price and status changes"
        assert any(alert.alert_type == 'price_change' for alert in alerts)
        assert any(alert.alert_type == 'status_change' for alert in alerts)