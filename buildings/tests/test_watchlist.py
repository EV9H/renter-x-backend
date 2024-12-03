import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from buildings.models import ApartmentWatchlist, BuildingWatchlist

@pytest.mark.django_db
class TestWatchlistAPI:
    def test_create_apartment_watchlist(self, api_client, sample_user, sample_apartment):
        api_client.force_authenticate(user=sample_user)
        response = api_client.post('/api/apartment-watchlist/', {
            'apartment': sample_apartment.id,
            'notify_price_change': True,
            'notify_availability_change': True
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert ApartmentWatchlist.objects.count() == 1

    def test_create_building_watchlist(self, api_client, sample_user, sample_building):
        api_client.force_authenticate(user=sample_user)
        response = api_client.post('/api/building-watchlist/', {
            'building': sample_building.id,
            'notify_new_units': True,
            'unit_type_preference': '2B2B'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert BuildingWatchlist.objects.count() == 1

    def test_list_watchlists(self, api_client, sample_user):
        api_client.force_authenticate(user=sample_user)
        response = api_client.get('/api/apartment-watchlist/')
        assert response.status_code == status.HTTP_200_OK

        response = api_client.get('/api/building-watchlist/')
        assert response.status_code == status.HTTP_200_OK