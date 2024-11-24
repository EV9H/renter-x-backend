import factory
from faker import Faker
from buildings.models import Building, Apartment, ApartmentPrice

fake = Faker()

class BuildingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Building

    name = factory.Faker('company')
    address = factory.Faker('street_address')
    postal_code = factory.Faker('postcode')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    website = factory.Faker('url')
    amenities = factory.Dict({
        'pool': factory.Faker('boolean'),
        'gym': factory.Faker('boolean'),
        'parking': factory.Faker('boolean')
    })

class ApartmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Apartment

    building = factory.SubFactory(BuildingFactory)
    unit_number = factory.Sequence(lambda n: f"{n+101}")
    floor = factory.LazyFunction(lambda: fake.random_int(min=1, max=20))
    bedrooms = factory.LazyFunction(lambda: fake.random_int(min=0, max=4))
    bathrooms = factory.LazyFunction(lambda: fake.random_int(min=1, max=4))
    area_sqft = factory.LazyFunction(lambda: fake.random_int(min=500, max=2000))
    apartment_type = factory.LazyAttribute(
        lambda o: f"{o.bedrooms}B{o.bathrooms}B" if o.bedrooms > 0 else "Studio"
    )
    status = factory.Iterator(['available', 'pending', 'leased', 'unavailable'])
    features = factory.Dict({
        'washer_dryer': factory.Faker('boolean'),
        'balcony': factory.Faker('boolean'),
        'view': factory.Faker('boolean')
    })

class ApartmentPriceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ApartmentPrice

    apartment = factory.SubFactory(ApartmentFactory)
    price = factory.LazyFunction(lambda: fake.random_int(min=1000, max=5000))
    start_date = factory.Faker('date_this_year')
    lease_term_months = factory.Iterator([6, 12, 18])
    is_special_offer = factory.Faker('boolean')
    special_offer_details = factory.LazyAttribute(
        lambda o: fake.sentence() if o.is_special_offer else None
    )