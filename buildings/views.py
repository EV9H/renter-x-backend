from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Building, Apartment, ApartmentPrice, ScrapingSource, ScrapingRun, PriceChange
from .serializers import (
    BuildingSerializer, ApartmentSerializer, ApartmentPriceSerializer,
    ScrapingSourceSerializer, ScrapingRunSerializer, PriceChangeSerializer,
    UserProfileSerializer
)

from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from .models import NewUserProfile
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken

class BuildingViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
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
    permission_classes = [AllowAny]

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
    permission_classes = [AllowAny]

    queryset = ApartmentPrice.objects.all()
    serializer_class = ApartmentPriceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['apartment', 'lease_term_months', 'is_special_offer']
    ordering_fields = ['price', 'start_date']

class ScrapingSourceViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]

    queryset = ScrapingSource.objects.all()
    serializer_class = ScrapingSourceSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'base_url']

class ScrapingRunViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]

    queryset = ScrapingRun.objects.all()
    serializer_class = ScrapingRunSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['source', 'status']
    ordering_fields = ['start_time', 'items_processed']

class PriceChangeViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]

    queryset = PriceChange.objects.all()
    serializer_class = PriceChangeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['apartment', 'scraping_run']
    ordering_fields = ['detected_at']



User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    try:
        data = request.data
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            return Response(
                {'error': 'Please provide both email and password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            email=email,
            password=password,
            username=email
        )

        refresh = RefreshToken.for_user(user)
        
        return Response({
            'id': user.id,
            'email': user.email,
            'token': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    try:
        data = request.data
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Please provide both email and password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=email, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'id': user.id,
                'email': user.email,
                'token': str(refresh.access_token),
                'refresh': str(refresh),
            })

        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

class UserProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        return NewUserProfile.objects.filter(user=self.request.user)

    def get_object(self):
        return self.get_queryset().first()

    @action(detail=False, methods=['get'])
    def me(self, request):
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def save_search(self, request):
        profile = self.get_object()
        current_searches = profile.saved_searches or []
        new_search = request.data.get('search_params', {})
        
        if new_search:
            current_searches.append(new_search)
            profile.saved_searches = current_searches
            profile.save()
        
        return Response({
            'saved_searches': profile.saved_searches
        })

    @action(detail=False, methods=['put'])
    def update_preferences(self, request):
        profile = self.get_object()
        notification_preferences = request.data.get('notification_preferences', {})
        
        if notification_preferences:
            profile.notification_preferences = notification_preferences
            profile.save()
        
        return Response({
            'notification_preferences': profile.notification_preferences
        })