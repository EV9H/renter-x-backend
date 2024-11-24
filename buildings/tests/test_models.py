import pytest
from django.core.exceptions import ValidationError
from buildings.models import Building, Apartment, ApartmentPrice

@pytest.mark.django_db
class TestBuilding:
    def test_create_building(self):
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="12345",
            city="Test City",
            state="TS",
            website="https://example.com",
            amenities={"pool": True, "gym": True}
        )
        assert building.name == "Test Building"
        assert building.amenities.get("pool") is True

    def test_building_str(self):
        building = Building.objects.create(
            name="Test Building",
            address="123 Test St",
            postal_code="12345",
            city="Test City",
            state="TS",
            website="https://example.com"
        )
        assert str(building) == "Test Building - 123 Test St"