from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BuildingViewSet, ApartmentViewSet, ApartmentPriceViewSet,
    ScrapingSourceViewSet, ScrapingRunViewSet, PriceChangeViewSet
)

router = DefaultRouter()
router.register(r'buildings', BuildingViewSet)
router.register(r'apartments', ApartmentViewSet)
router.register(r'apartment-prices', ApartmentPriceViewSet)
router.register(r'scraping-sources', ScrapingSourceViewSet)
router.register(r'scraping-runs', ScrapingRunViewSet)
router.register(r'price-changes', PriceChangeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]