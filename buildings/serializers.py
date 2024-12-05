from rest_framework import serializers
from .models import Region, Building, Apartment, ApartmentPrice, ScrapingSource, ScrapingRun, PriceChange, ApartmentWatchlist, BuildingWatchlist, WatchlistAlert

class RegionSerializer(serializers.ModelSerializer):
    borough_display = serializers.CharField(source='get_borough_display', read_only=True)
    neighborhood_display = serializers.CharField(source='get_neighborhood_display', read_only=True)
    
    class Meta:
        model = Region
        fields = ['id', 'name', 'borough', 'borough_display', 
                 'neighborhood', 'neighborhood_display', 'description']

class BuildingSerializer(serializers.ModelSerializer):
    region_details = RegionSerializer(source='region', read_only=True)
    
    class Meta:
        model = Building
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.region:
            representation['region_name'] = f"{instance.region.get_borough_display()} - {instance.region.get_neighborhood_display()}"
        return representation

# class ApartmentSerializer(serializers.ModelSerializer):
#     building_name = serializers.CharField(source='building.name', read_only=True)
#     current_price = serializers.SerializerMethodField()

#     class Meta:
#         model = Apartment
#         fields = [
#             'id', 'building', 'building_name', 'unit_number', 'floor',
#             'bedrooms', 'bathrooms', 'area_sqft', 'apartment_type',
#             'status', 'features', 'current_price', 'created_at', 'updated_at'
#         ]

#     def get_current_price(self, obj):
#         latest_price = obj.price_history.order_by('-start_date').first()
#         if latest_price:
#             return {
#                 'price': latest_price.price,
#                 'lease_term_months': latest_price.lease_term_months,
#                 'is_special_offer': latest_price.is_special_offer,
#                 'special_offer_details': latest_price.special_offer_details
#             }
#         return None
class ApartmentSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()
    price_changes = serializers.SerializerMethodField()
    last_scraping_run = serializers.SerializerMethodField()
    
    class Meta:
        model = Apartment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_current_price(self, obj):
        latest_price = obj.price_history.order_by('-start_date', '-created_at').first()
        if latest_price:
            return {
                'price': latest_price.price,
                'start_date': latest_price.start_date,
                'lease_term_months': latest_price.lease_term_months
            }
        return None

    def get_price_changes(self, obj):
        # Get last 5 price changes
        changes = obj.price_changes.order_by('-detected_at')[:5]
        return [{
            'old_price': change.old_price,
            'new_price': change.new_price,
            'detected_at': change.detected_at
        } for change in changes]

    def get_last_scraping_run(self, obj):
        last_change = obj.price_changes.order_by('-detected_at').first()
        if last_change and last_change.scraping_run:
            return {
                'id': last_change.scraping_run.id,
                'date': last_change.scraping_run.start_time,
            }
        return None
class ApartmentPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentPrice
        fields = '__all__'

class ScrapingSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapingSource
        fields = '__all__'

class ScrapingRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapingRun
        fields = '__all__'

class PriceChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceChange
        fields = '__all__'


from .models import NewUserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = NewUserProfile
        fields = ['id', 'email','phone_number', 'preferred_contact_method',
            'apartment_preferences']

    def create(self, validated_data):
        user = validated_data.pop('user', None)
        if not user:
            raise serializers.ValidationError({"user": "This field is required."})
        return NewUserProfile.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class ApartmentWatchlistSerializer(serializers.ModelSerializer):
    apartment_details = ApartmentSerializer(source='apartment', read_only=True)

    class Meta:
        model = ApartmentWatchlist
        fields = ['id', 'apartment', 'apartment_details', 'notify_price_change', 
                 'notify_availability_change', 'created_at', 'last_notified']
        read_only_fields = ['created_at', 'last_notified']

class BuildingWatchlistSerializer(serializers.ModelSerializer):
    building_details = BuildingSerializer(source='building', read_only=True)

    class Meta:
        model = BuildingWatchlist
        fields = ['id', 'building', 'building_details', 'notify_new_units', 
                 'unit_type_preference', 'max_price', 'created_at', 'last_notified']
        read_only_fields = ['created_at', 'last_notified']


class WatchlistAlertSerializer(serializers.ModelSerializer):
    building_details = BuildingSerializer(source='building', read_only=True)
    apartment_details = ApartmentSerializer(source='apartment', read_only=True)

    class Meta:
        model = WatchlistAlert
        fields = [
            'id', 'alert_type', 'message', 'created_at', 'read',
            'building', 'building_details',
            'apartment', 'apartment_details'
        ]
        read_only_fields = ['created_at']