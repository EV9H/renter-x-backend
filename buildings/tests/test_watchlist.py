import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from buildings.models import *
from .factories import *
@pytest.mark.django_db
class TestWatchlistAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
        self.building = BuildingFactory()
        self.apartment = ApartmentFactory(building=self.building)

    def test_create_apartment_watchlist(self):
        data = {
            'apartment': self.apartment.id,
            'notify_price_change': True,
            'notify_availability_change': True
        }
        
        response = self.client.post(
            reverse('apartment-watchlist-list'),
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['apartment'] == self.apartment.id
        assert response.data['notify_price_change'] is True

    def test_create_building_watchlist(self):
        data = {
            'building': self.building.id,
            'notify_new_units': True,
            'unit_type_preference': '1B1B',
            'max_price': '3000.00'
        }
        
        response = self.client.post(
            reverse('building-watchlist-list'),
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['building'] == self.building.id
        assert response.data['unit_type_preference'] == '1B1B'

    def test_list_watchlists(self):
        # Create some watchlist items
        apartment_watchlist = ApartmentWatchlistFactory(
            user=self.user,
            apartment=self.apartment
        )
        building_watchlist = BuildingWatchlistFactory(
            user=self.user,
            building=self.building
        )
        
        # Test apartment watchlist
        response = self.client.get(reverse('apartment-watchlist-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        
        # Test building watchlist
        response = self.client.get(reverse('building-watchlist-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_delete_from_watchlist(self):
        # Create watchlist items
        apartment_watchlist = ApartmentWatchlistFactory(
            user=self.user,
            apartment=self.apartment
        )
        building_watchlist = BuildingWatchlistFactory(
            user=self.user,
            building=self.building
        )
        
        # Delete apartment watchlist
        response = self.client.delete(
            reverse('apartment-watchlist-detail', kwargs={'pk': apartment_watchlist.pk})
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Delete building watchlist
        response = self.client.delete(
            reverse('building-watchlist-detail', kwargs={'pk': building_watchlist.pk})
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_update_watchlist_preferences(self):
        apartment_watchlist = ApartmentWatchlistFactory(
            user=self.user,
            apartment=self.apartment
        )
        
        updated_data = {
            'apartment': self.apartment.id,
            'notify_price_change': False,
            'notify_availability_change': True
        }
        
        response = self.client.put(
            reverse('apartment-watchlist-detail', kwargs={'pk': apartment_watchlist.pk}),
            updated_data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['notify_price_change'] is False

    def test_unauthorized_watchlist_access(self):
        self.client.force_authenticate(user=None)
        
        response = self.client.get(reverse('apartment-watchlist-list'))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = self.client.get(reverse('building-watchlist-list'))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED