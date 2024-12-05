# buildings/tests/conftest.py
import pytest
from rest_framework.test import APIClient
from .factories import (
    BuildingFactory, ApartmentFactory, UserFactory,
    ApartmentPriceFactory, RegionFactory,
    ApartmentWatchlistFactory, BuildingWatchlistFactory
)

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def region():
    return RegionFactory()

@pytest.fixture
def building(region):
    return BuildingFactory(region=region)

@pytest.fixture
def apartment(building):
    return ApartmentFactory(building=building)

@pytest.fixture
def apartment_price(apartment):
    return ApartmentPriceFactory(apartment=apartment)

@pytest.fixture
def building_watchlist(user, building):
    return BuildingWatchlistFactory(user=user, building=building)

@pytest.fixture
def apartment_watchlist(user, apartment):
    return ApartmentWatchlistFactory(user=user, apartment=apartment)

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client