import pytest
from rest_framework.test import APIClient
from rest_framework import status
from buildings.models import Building, Apartment
from django.urls import reverse

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def sample_building():
    return Building.objects.create(
        name="Test Building",
        address="123 Test St",
        postal_code="12345",
        city="Test City",
        state="TS",
        website="https://example.com",
        amenities={"pool": True, "gym": True}
    )

@pytest.fixture
def sample_apartment(sample_building):
    return Apartment.objects.create(
        building=sample_building,
        unit_number="101",
        floor=1,
        bedrooms=2,
        bathrooms=2,
        area_sqft=1000,
        apartment_type="2B2B",
        status="available",
        features={"washer_dryer": True}
    )
@pytest.mark.django_db
class TestBuildingAPI:
    """Tests for Building API endpoints"""

    def test_list_buildings(self, api_client, sample_building):
        """
        Given: A building exists in the database
        When: Making GET request to buildings list endpoint
        Then: Should return 200 and list containing the building
        """
        url = reverse('building-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == sample_building.name

    def test_create_building(self, api_client):
        """
        Given: Valid building data
        When: Making POST request to create building
        Then: Should return 201 and create new building
        """
        url = reverse('building-list')
        data = {
            "name": "New Building",
            "address": "456 New St",
            "postal_code": "67890",
            "city": "New City",
            "state": "NS",
            "website": "https://example.com",
            "amenities": {"pool": True}
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Building.objects.count() == 1
        assert Building.objects.get().name == "New Building"

@pytest.mark.django_db
class TestApartmentAPI:
    """Tests for Apartment API endpoints"""

    def test_list_apartments(self, api_client, sample_apartment):
        """
        Given: An apartment exists in the database
        When: Making GET request to apartments list endpoint
        Then: Should return 200 and list containing the apartment
        """
        url = reverse('apartment-list')
        response = api_client.get(url)
        print(f"\nResponse data: {response.data}")  # Added debug print
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['unit_number'] == sample_apartment.unit_number
