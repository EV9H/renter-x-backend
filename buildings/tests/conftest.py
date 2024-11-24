import pytest
from rest_framework.test import APIClient
from .factories import BuildingFactory, ApartmentFactory

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def sample_building():
    return BuildingFactory()

@pytest.fixture
def sample_apartment(sample_building):
    return ApartmentFactory(building=sample_building)

@pytest.fixture
def sample_buildings():
    return BuildingFactory.create_batch(3)

@pytest.fixture
def sample_apartments(sample_building):
    return ApartmentFactory.create_batch(3, building=sample_building)


