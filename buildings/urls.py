from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BuildingViewSet, ApartmentViewSet, ApartmentPriceViewSet,
    ScrapingSourceViewSet, ScrapingRunViewSet, PriceChangeViewSet,
    UserProfileViewSet, ApartmentWatchlistViewSet,BuildingWatchlistViewSet,
    WatchlistAlertViewSet,
    # BuildingAdminViewSet, 
    # ApartmentAdminViewSet,
    # PriceChangeAdminViewSet
)

from . import views
from rest_framework_simplejwt.views import TokenRefreshView
router = DefaultRouter()
router.register(r'buildings', BuildingViewSet)
router.register(r'apartments', ApartmentViewSet)
router.register(r'apartment-prices', ApartmentPriceViewSet)
router.register(r'scraping-sources', ScrapingSourceViewSet)
router.register(r'scraping-runs', ScrapingRunViewSet)
router.register(r'price-changes', PriceChangeViewSet)
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'apartment-watchlist', ApartmentWatchlistViewSet, basename='apartment-watchlist')
router.register(r'building-watchlist', BuildingWatchlistViewSet, basename='building-watchlist')
router.register(r'watchlist-alerts', WatchlistAlertViewSet, basename='watchlist-alerts')
# router.register(r'admin/buildings', BuildingAdminViewSet)
# router.register(r'admin/apartments', ApartmentAdminViewSet)
# router.register(r'admin/price-changes', PriceChangeAdminViewSet)
urlpatterns = [
    path('', include(router.urls)),
    path('auth/signup/', views.signup, name='signup'),
    path('auth/login/', views.login, name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]