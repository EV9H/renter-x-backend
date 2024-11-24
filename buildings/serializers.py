from rest_framework import serializers
from .models import Building, Apartment, ApartmentPrice, ScrapingSource, ScrapingRun, PriceChange

class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = '__all__'

class ApartmentSerializer(serializers.ModelSerializer):
    building_name = serializers.CharField(source='building.name', read_only=True)
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = Apartment
        fields = [
            'id', 'building', 'building_name', 'unit_number', 'floor',
            'bedrooms', 'bathrooms', 'area_sqft', 'apartment_type',
            'status', 'features', 'current_price', 'created_at', 'updated_at'
        ]

    def get_current_price(self, obj):
        latest_price = obj.price_history.order_by('-start_date').first()
        if latest_price:
            return {
                'price': latest_price.price,
                'lease_term_months': latest_price.lease_term_months,
                'is_special_offer': latest_price.is_special_offer,
                'special_offer_details': latest_price.special_offer_details
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
