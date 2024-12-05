from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Max
from .models import Building, Apartment, ApartmentPrice, ScrapingSource, ScrapingRun, PriceChange, ApartmentWatchlist, BuildingWatchlist,WatchlistAlert
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .serializers import (
    BuildingSerializer, ApartmentSerializer, ApartmentPriceSerializer,
    ScrapingSourceSerializer, ScrapingRunSerializer, PriceChangeSerializer,
    UserProfileSerializer, ApartmentWatchlistSerializer, BuildingWatchlistSerializer, 
    WatchlistAlertSerializer
)

from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.contrib.auth import authenticate, get_user_model
from .models import NewUserProfile
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal

import logging

logger = logging.getLogger(__name__)

class BuildingViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Building.objects.all().order_by('id')
    serializer_class = BuildingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['postal_code', 'city', 'state','region']
    search_fields = ['name', 'address']
    ordering_fields = ['name', 'created_at']

    @action(detail=True, methods=['get'])
    def apartments(self, request, pk=None):
        building = self.get_object()
        apartments = building.apartments.all()
        serializer = ApartmentSerializer(apartments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        building = self.get_object()
        apartments = building.apartments.all()
        
        # Group by apartment type and calculate stats
        stats = {}
        apartment_types = set()
        
        for apt in apartments:
            apt_type = apt.apartment_type
            apartment_types.add(apt_type)
            
            if apt_type not in stats:
                stats[apt_type] = {
                    'count': 0,
                    'available_count': 0,
                    'avg_price': Decimal('0'),
                    'min_price': None,
                    'max_price': None,
                    'total_price': Decimal('0'),
                    'available_units': []
                }
            
            current_price = apt.price_history.order_by('-start_date').first()
            if current_price:
                price = current_price.price
                stats[apt_type]['count'] += 1
                
                if apt.status == 'available':
                    stats[apt_type]['available_count'] += 1
                    stats[apt_type]['total_price'] += price
                    stats[apt_type]['available_units'].append({
                        'unit': apt.unit_number,
                        'price': price
                    })
                    
                    if stats[apt_type]['min_price'] is None or price < stats[apt_type]['min_price']:
                        stats[apt_type]['min_price'] = price
                    if stats[apt_type]['max_price'] is None or price > stats[apt_type]['max_price']:
                        stats[apt_type]['max_price'] = price

        # Calculate averages for available units
        for apt_type in stats:
            if stats[apt_type]['available_count'] > 0:
                stats[apt_type]['avg_price'] = stats[apt_type]['total_price'] / stats[apt_type]['available_count']

        return Response(stats)
# class ApartmentViewSet(viewsets.ModelViewSet):
#     permission_classes = [AllowAny]

#     queryset = Apartment.objects.all().order_by('id')
#     serializer_class = ApartmentSerializer
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
#     filterset_fields = ['building', 'status', 'bedrooms', 'bathrooms']
#     search_fields = ['unit_number', 'apartment_type']
#     ordering_fields = ['area_sqft', 'floor', 'created_at']

#     @action(detail=True, methods=['get'])
#     def price_history(self, request, pk=None):
#         apartment = self.get_object()
#         prices = apartment.price_history.all().order_by('-start_date')
#         serializer = ApartmentPriceSerializer(prices, many=True)
#         return Response(serializer.data)
class ApartmentViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['building', 'status', 'bedrooms', 'bathrooms', "apartment_type"]
    
    @action(detail=False, methods=['GET'])
    def debug(self, request):
        apartments = Apartment.objects.all().values('id', 'unit_number', 'building_id')
        return Response(apartments)
    def get_queryset(self):
        queryset = Apartment.objects.all()
        
        # Get only current available apartments by default
        status = self.request.query_params.get('status', 'available')
        if status != 'all':
            queryset = queryset.filter(status=status)
            
        # Include price history and changes
        queryset = queryset.prefetch_related(
            'price_history',
            'price_changes'
        ).select_related('building')
        
        return queryset
    def get_object(self):
        try:
            obj = super().get_object()
            print(f"Found apartment with ID: {obj.id}")
            return obj
        except Exception as e:
            print(f"Error getting apartment: {str(e)}")
            raise
    def update(self, request, *args, **kwargs):
        try:
            apartment_id = kwargs.get('pk')
            # First check if apartment exists
            try:
                instance = Apartment.objects.get(id=apartment_id)
            except Apartment.DoesNotExist:
                return Response(
                    {"detail": f"Apartment with ID {apartment_id} does not exist."},
                    status=status.HTTP_404_NOT_FOUND
                )

            print(f"Found apartment {instance.id}, proceeding with update")
            serializer = self.get_serializer(instance, data=request.data)
            
            if not serializer.is_valid():
                print("Validation errors:", serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
            self.perform_update(serializer)
            return Response(serializer.data)
        except Exception as e:
            print(f"Update error: {str(e)}")
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

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

    @action(detail=False, methods=['GET'])
    def latest_end_time(self, request):
        latest_end_time = ScrapingRun.objects.filter(
            status='completed'
        ).aggregate(
            latest_end=Max('end_time')
        )['latest_end']

        return Response({
            'latest_end_time': latest_end_time
        })
    
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

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        profile = self.get_object()
        if not profile:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


from rest_framework.exceptions import ValidationError
from django.db import IntegrityError

class BuildingWatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BuildingWatchlistSerializer

    def get_queryset(self):
        return BuildingWatchlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            # Instead of throwing an error, return the existing watchlist item
            building_id = serializer.validated_data['building'].id
            existing_item = BuildingWatchlist.objects.get(
                user=self.request.user,
                building_id=building_id
            )
            serializer.instance = existing_item

class ApartmentWatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ApartmentWatchlistSerializer

    def get_queryset(self):
        return ApartmentWatchlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            # Instead of throwing an error, return the existing watchlist item
            apartment_id = serializer.validated_data['apartment'].id
            existing_item = ApartmentWatchlist.objects.get(
                user=self.request.user,
                apartment_id=apartment_id
            )
            serializer.instance = existing_item


class WatchlistAlertViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WatchlistAlertSerializer

    def get_queryset(self):
        return WatchlistAlert.objects.filter(
            user=self.request.user
        ).select_related(
            'building',
            'apartment'
        ).order_by('-created_at')

    @action(detail=True, methods=['POST'])
    def mark_as_read(self, request, pk=None):
        alert = self.get_object()
        alert.read = True
        alert.save()
        return Response(self.get_serializer(alert).data)

    @action(detail=False, methods=['POST'])
    def mark_all_as_read(self, request):
        self.get_queryset().update(read=True)
        return Response({'status': 'success'})





class AdminBuildingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer

    @action(detail=True, methods=['post'])
    def bulk_update_amenities(self, request, pk=None):
        building = self.get_object()
        building.amenities.update(request.data)
        building.save()
        return Response(building.amenities)

class AdminApartmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer

    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        logger.info(f"Received request to update price for apartment ID {pk}")

        try:
            apartment = self.get_object()
            logger.info(f"Apartment found: {apartment}")
        except ObjectDoesNotExist:
            logger.error(f"Apartment with ID {pk} not found.")
            return Response({"detail": "Apartment not found."}, status=status.HTTP_404_NOT_FOUND)

        price = request.data.get('price')
        lease_term_months = request.data.get('lease_term_months')

        if not price or not lease_term_months:
            logger.warning(f"Invalid data provided: price={price}, lease_term_months={lease_term_months}")
            return Response({"detail": "Price and lease term are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the most recent price
        latest_price_entry = apartment.price_history.order_by('-start_date').first()
        logger.info(f"Latest price entry: {latest_price_entry}")

        # Check if the price is the same
        if latest_price_entry and latest_price_entry.price == float(price):
            logger.info("Price is unchanged; no update required.")
            return Response({"detail": "Price is unchanged."}, status=status.HTTP_400_BAD_REQUEST)

        # Create a new price entry
        try:
            new_price_entry = ApartmentPrice.objects.create(
                apartment=apartment,
                price=price,
                lease_term_months=lease_term_months,
                start_date=timezone.now()
            )
            logger.info(f"New price entry created: {new_price_entry}")
        except Exception as e:
            logger.error(f"Failed to create new price entry: {e}")
            return Response({"detail": "Failed to update price."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Record the price change
        if latest_price_entry:
            try:
                price_change = PriceChange.objects.create(
                    apartment=apartment,
                    old_price=latest_price_entry.price,
                    new_price=price,
                    scraping_run=None  # Replace with appropriate ScrapingRun if applicable
                )
                logger.info(f"Price change recorded: {price_change}")
            except Exception as e:
                logger.error(f"Failed to create PriceChange entry: {e}")
                return Response({"detail": "Failed to record price change."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.info("No previous price entry found; skipping price change record.")

        return Response({"detail": "Price updated successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        apartment = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in [choice[0] for choice in Apartment.ApartmentStatus.choices]:
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        apartment.status = new_status
        apartment.save()
        return Response({'status': 'success'})

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
