from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Building, Apartment, ApartmentPrice, ScrapingSource, ScrapingRun, PriceChange
from .serializers import (
    BuildingSerializer, ApartmentSerializer, ApartmentPriceSerializer,
    ScrapingSourceSerializer, ScrapingRunSerializer, PriceChangeSerializer
)

class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.all().order_by('id')
    serializer_class = BuildingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['postal_code', 'city', 'state']
    search_fields = ['name', 'address']
    ordering_fields = ['name', 'created_at']

    @action(detail=True, methods=['get'])
    def apartments(self, request, pk=None):
        building = self.get_object()
        apartments = building.apartments.all()
        serializer = ApartmentSerializer(apartments, many=True)
        return Response(serializer.data)

class ApartmentViewSet(viewsets.ModelViewSet):
    queryset = Apartment.objects.all().order_by('id')
    serializer_class = ApartmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['building', 'status', 'bedrooms', 'bathrooms']
    search_fields = ['unit_number', 'apartment_type']
    ordering_fields = ['area_sqft', 'floor', 'created_at']

    @action(detail=True, methods=['get'])
    def price_history(self, request, pk=None):
        apartment = self.get_object()
        prices = apartment.price_history.all().order_by('-start_date')
        serializer = ApartmentPriceSerializer(prices, many=True)
        return Response(serializer.data)

class ApartmentPriceViewSet(viewsets.ModelViewSet):
    queryset = ApartmentPrice.objects.all()
    serializer_class = ApartmentPriceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['apartment', 'lease_term_months', 'is_special_offer']
    ordering_fields = ['price', 'start_date']

class ScrapingSourceViewSet(viewsets.ModelViewSet):
    queryset = ScrapingSource.objects.all()
    serializer_class = ScrapingSourceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'base_url']

class ScrapingRunViewSet(viewsets.ModelViewSet):
    queryset = ScrapingRun.objects.all()
    serializer_class = ScrapingRunSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['source', 'status']
    ordering_fields = ['start_time', 'items_processed']

class PriceChangeViewSet(viewsets.ModelViewSet):
    queryset = PriceChange.objects.all()
    serializer_class = PriceChangeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['apartment', 'scraping_run']
    ordering_fields = ['detected_at']