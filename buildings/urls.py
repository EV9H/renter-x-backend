from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter
from .views import (
    BuildingViewSet, ApartmentViewSet, ApartmentPriceViewSet,
    ScrapingSourceViewSet, ScrapingRunViewSet, PriceChangeViewSet,
    UserProfileViewSet, ApartmentWatchlistViewSet,BuildingWatchlistViewSet,
    WatchlistAlertViewSet,
    AdminBuildingViewSet, 
    AdminApartmentViewSet,
    AdminRegionViewSet,
    # PriceChangeAdminViewSet
)
from .forum import views as forum_views

from . import views
from rest_framework_simplejwt.views import TokenRefreshView,TokenObtainPairView
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
router.register(r'admin/buildings', AdminBuildingViewSet, basename='admin-building')
router.register(r'admin/apartments', AdminApartmentViewSet, basename='admin-apartment')
router.register(r'admin/regions', AdminRegionViewSet, basename='admin-region')


# Forum routes
router.register(r'forum/categories', forum_views.CategoryViewSet, basename='forum-category')
router.register(r'forum/posts', forum_views.PostViewSet, basename='forum-post')
router.register(r'forum/tags', forum_views.TagViewSet, basename='forum-tag')
router.register(r'forum/drafts', forum_views.PostDraftViewSet, basename='forum-draft')

# Nested router for comments
posts_router = NestedSimpleRouter(router, r'forum/posts', lookup='post')
posts_router.register(r'comments', forum_views.CommentViewSet, basename='forum-post-comments')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/signup/', views.signup, name='signup'),
    path('auth/login/', views.login, name='login'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(posts_router.urls)),

]