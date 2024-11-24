import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from buildings.models import Building, Apartment, ApartmentPrice
from .factories import BuildingFactory, ApartmentFactory, ApartmentPriceFactory

@pytest.mark.django_db
class TestBuildingViewSet:
    def test_retrieve_building(self, api_client, sample_building):
        url = reverse('building-detail', kwargs={'pk': sample_building.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == sample_building.name

    def test_update_building(self, api_client, sample_building):
        url = reverse('building-detail', kwargs={'pk': sample_building.pk})
        data = {
            "name": "Updated Building",
            "address": sample_building.address,
            "postal_code": sample_building.postal_code,
            "city": sample_building.city,
            "state": sample_building.state,
            "website": sample_building.website,
            "amenities": sample_building.amenities
        }
        response = api_client.put(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "Updated Building"

    def test_delete_building(self, api_client, sample_building):
        url = reverse('building-detail', kwargs={'pk': sample_building.pk})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Building.objects.count() == 0

    def test_building_apartments_action(self, api_client, sample_building):
        # Create some apartments for the building
        ApartmentFactory.create_batch(3, building=sample_building)
        
        url = reverse('building-apartments', kwargs={'pk': sample_building.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

@pytest.mark.django_db
class TestApartmentViewSet:
    def test_retrieve_apartment(self, api_client, sample_apartment):
        url = reverse('apartment-detail', kwargs={'pk': sample_apartment.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['unit_number'] == sample_apartment.unit_number

    def test_update_apartment(self, api_client, sample_apartment):
        url = reverse('apartment-detail', kwargs={'pk': sample_apartment.pk})
        data = {
            "building": sample_apartment.building.pk,
            "unit_number": "Updated-101",
            "floor": sample_apartment.floor,
            "bedrooms": sample_apartment.bedrooms,
            "bathrooms": sample_apartment.bathrooms,
            "area_sqft": sample_apartment.area_sqft,
            "apartment_type": sample_apartment.apartment_type,
            "status": sample_apartment.status,
            "features": sample_apartment.features
        }
        response = api_client.put(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['unit_number'] == "Updated-101"

    def test_delete_apartment(self, api_client, sample_apartment):
        url = reverse('apartment-detail', kwargs={'pk': sample_apartment.pk})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Apartment.objects.count() == 0

    def test_apartment_price_history(self, api_client, sample_apartment):
        # Create some price history
        ApartmentPriceFactory.create_batch(3, apartment=sample_apartment)
        
        url = reverse('apartment-price-history', kwargs={'pk': sample_apartment.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3