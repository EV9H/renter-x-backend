# buildings/tests/test_views.py
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse
from buildings.models import Building, Apartment, Region
from .factories import (
    UserFactory, BuildingFactory, ApartmentFactory, 
    RegionFactory, ApartmentPriceFactory
)
from decimal import Decimal

@pytest.mark.django_db
class TestBuildingViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_staff=True)  # Create admin user
        self.client.force_authenticate(user=self.user)
        self.region = RegionFactory()
        self.building_data = {
            "name": "Test Building",
            "address": "123 Test St",
            "postal_code": "10001",
            "city": "New York",
            "state": "NY",
            "website": "https://testbuilding.com",
            "amenities": {"gym": True, "pool": False},
            "region": self.region.id
        }

    def test_list_buildings(self):
        buildings = BuildingFactory.create_batch(3, region=self.region)
        response = self.client.get(reverse('building-list'))
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3
        assert response.data['results'][0]['name'] == buildings[0].name

    def test_create_building(self):
        response = self.client.post(
            reverse('building-list'),
            self.building_data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == self.building_data['name']
        assert Building.objects.count() == 1

    def test_retrieve_building(self):
        building = BuildingFactory(region=self.region)
        response = self.client.get(
            reverse('building-detail', kwargs={'pk': building.pk})
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == building.name
        assert response.data['region'] == building.region.id

    def test_update_building(self):
        building = BuildingFactory(region=self.region)
        updated_data = {
            **self.building_data,
            "name": "Updated Building Name"
        }
        
        response = self.client.put(
            reverse('building-detail', kwargs={'pk': building.pk}),
            updated_data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "Updated Building Name"

    def test_partial_update_building(self):
        building = BuildingFactory(region=self.region)
        response = self.client.patch(
            reverse('building-detail', kwargs={'pk': building.pk}),
            {"name": "Updated Name"},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == "Updated Name"

    def test_delete_building(self):
        building = BuildingFactory(region=self.region)
        response = self.client.delete(
            reverse('building-detail', kwargs={'pk': building.pk})
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Building.objects.filter(pk=building.pk).exists()

    def test_building_apartments_action(self):
        building = BuildingFactory(region=self.region)
        apartments = ApartmentFactory.create_batch(3, building=building)
        
        response = self.client.get(
            reverse('building-apartments', kwargs={'pk': building.pk})
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_building_stats_action(self):
        building = BuildingFactory(region=self.region)
        # Create apartments with different types and prices
        apt1 = ApartmentFactory(
            building=building,
            bedrooms=1,
            bathrooms=1,
            status='available'
        )
        apt2 = ApartmentFactory(
            building=building,
            bedrooms=2,
            bathrooms=2,
            status='available'
        )
        
        # Create prices for apartments
        ApartmentPriceFactory(apartment=apt1, price=Decimal('2000'))
        ApartmentPriceFactory(apartment=apt2, price=Decimal('3000'))
        
        response = self.client.get(
            reverse('building-stats', kwargs={'pk': building.pk})
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert '1B1B' in response.data
        assert '2B2B' in response.data
        assert response.data['1B1B']['count'] == 1
        assert response.data['2B2B']['count'] == 1

    def test_filter_buildings_by_region(self):
        region1 = RegionFactory(borough='MAN')
        region2 = RegionFactory(borough='BRK')
        
        # Create buildings with specific regions
        building1 = BuildingFactory(region=region1)
        building2 = BuildingFactory(region=region2)
        
        # Get buildings for region1 only
        response = self.client.get(
            reverse('building-list'),
            {'region': region1.id},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['region'] == region1.id

    def test_unauthorized_access(self):
        # Remove authentication
        self.client.force_authenticate(user=None)
        
        # Test endpoints that should require authentication
        admin_endpoints = [
            ('post', reverse('admin-building-list'), self.building_data),
            ('put', reverse('admin-building-detail', kwargs={'pk': 1}), self.building_data),
            ('delete', reverse('admin-building-detail', kwargs={'pk': 1}), None),
        ]
        
        for method, url, data in admin_endpoints:
            response = getattr(self.client, method)(url, data, format='json')
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, f"Expected 401 for {method} {url}"

        # Test public endpoints that should be accessible
        public_url = reverse('building-list')
        response = self.client.get(public_url)
        assert response.status_code == status.HTTP_200_OK, "Building list should be public"

    @pytest.mark.django_db
    def test_bulk_update_amenities(self):
        user = UserFactory(is_staff=True)
        self.client.force_authenticate(user=user)

        building = BuildingFactory()
        amenities_update = {
            "gym": True,
            "pool": True,
            "parking": False
        }

        response = self.client.post(
            reverse('admin-building-bulk-update-amenities', kwargs={'pk': building.pk}),
            data=amenities_update,
            format='json'
        )

        assert response.status_code == 200
        building.refresh_from_db()
        assert building.amenities == amenities_update

    @pytest.mark.django_db
    def test_building_list_without_region(self):
        BuildingFactory.create_batch(2, region=None)

        response = self.client.get(reverse('building-list'), {'region': ''})
        assert response.status_code == 200
        assert len(response.data['results']) == 2
    @pytest.mark.django_db
    def test_filter_buildings_by_city(self):
        BuildingFactory(city="CityA")
        BuildingFactory(city="CityB")

        response = self.client.get(reverse('building-list'), {'city': 'CityA'})
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['city'] == 'CityA'

    @pytest.mark.django_db
    def test_order_buildings_by_name(self):
        BuildingFactory(name="Zeta Building")
        BuildingFactory(name="Alpha Building")

        response = self.client.get(reverse('building-list'), {'ordering': 'name'})
        assert response.status_code == 200
        results = response.data['results']
        assert results[0]['name'] == "Alpha Building"
        assert results[1]['name'] == "Zeta Building"

    @pytest.mark.django_db
    def test_retrieve_nonexistent_building(self):
        response = self.client.get(reverse('building-detail', kwargs={'pk': 999}))
        assert response.status_code == 404
        assert response.data['detail']== 'No Building matches the given query.'

    # @pytest.mark.django_db
    # def test_bulk_create_buildings(self):
    #     admin_user = UserFactory(is_staff=True)
    #     self.client.force_authenticate(user=admin_user)

    #     building_data = [
    #         {"name": "Building 1", "address": "Address 1", "city": "CityA", "state": "StateA"},
    #         {"name": "Building 2", "address": "Address 2", "city": "CityB", "state": "StateB"},
    #     ]

    #     response = self.client.post(reverse('admin-building-bulk-create'), data=building_data, format='json')
    #     assert response.status_code == 201
    #     assert len(response.data) == len(building_data)

    @pytest.mark.django_db
    def test_apartment_queryset_status_filter(self):
        ApartmentFactory(status='available')
        ApartmentFactory(status='unavailable')

        response = self.client.get(reverse('apartment-list'), {'status': 'available'})
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['status'] == 'available'

    # @pytest.mark.django_db
    # def test_building_unauthorized_access(self):
    #     response = self.client.get(reverse('building-list'))
    #     assert response.status_code == 403  # Assuming access requires authentication
    
    @pytest.mark.django_db
    def test_apartment_debug_endpoint(self):
        ApartmentFactory.create_batch(3)
        response = self.client.get(reverse('apartment-debug'))
        assert response.status_code == 200
        assert len(response.data) == 3

    @pytest.mark.django_db
    def test_building_apartments_list(self):
        building = BuildingFactory()
        ApartmentFactory.create_batch(3, building=building)

        response = self.client.get(reverse('building-apartments', kwargs={'pk': building.id}))
        assert response.status_code == 200
        assert len(response.data) == 3

    @pytest.mark.django_db
    def test_invalid_building_creation(self):
        admin_user = UserFactory(is_staff=True)
        self.client.force_authenticate(user=admin_user)

        invalid_data = {"name": ""}
        response = self.client.post(reverse('building-list'), data=invalid_data, format='json')
        assert response.status_code == 400
        assert 'name' in response.data

    @pytest.mark.django_db
    def test_building_stats_no_apartments(self):
        building = BuildingFactory()
        response = self.client.get(reverse('building-stats', kwargs={'pk': building.id}))
        assert response.status_code == 200
        assert response.data == {}  # Expect empty stats

    @pytest.mark.django_db
    def test_building_stats_with_apartments(self):
        building = BuildingFactory()
        apt = ApartmentFactory(building=building, apartment_type="1B1B", status="available")
        ApartmentPriceFactory(apartment=apt, price=2000)

        response = self.client.get(reverse('building-stats', kwargs={'pk': building.id}))
        assert response.status_code == 200
        assert "1B1B" in response.data
        assert response.data["1B1B"]["count"] == 1

    # @pytest.mark.django_db
    # def test_bulk_update_amenities(self):
    #     admin_user = UserFactory(is_staff=True)
    #     self.client.force_authenticate(user=admin_user)

    #     building = BuildingFactory()
    #     amenities = {"gym": True, "pool": False}
    #     response = self.client.post(
    #         reverse('admin-building-bulk-update-amenities', kwargs={'pk': building.id}),
    #         data=amenities,
    #         format='json',
    #     )
    #     assert response.status_code == 200
    #     assert building.amenities == amenities


    @pytest.mark.django_db
    def test_admin_update_price(self):
        admin_user = UserFactory(is_staff=True)
        self.client.force_authenticate(user=admin_user)

        apt = ApartmentFactory()
        price_data = {"price": 2500, "lease_term_months": 12}
        response = self.client.post(
            reverse('admin-apartment-update-price', kwargs={'pk': apt.id}),
            data=price_data,
            format='json',
        )
        assert response.status_code == 200
