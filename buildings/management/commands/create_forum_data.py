from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from buildings.forum.models import Category

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates initial forum data'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'New Student Checklist',
                'slug': 'new-student',
                'description': 'Essential information for new students'
            },
            {
                'name': 'Building Recommendations',
                'slug': 'recommendations',
                'description': 'Find and discuss the best buildings'
            },
            {
                'name': 'Neighborhood Guides',
                'slug': 'neighborhood',
                'description': 'Explore different neighborhoods'
            },
            {
                'name': 'Rental Tips & Advice',
                'slug': 'tips',
                'description': 'Tips and tricks for renting'
            },
            {
                'name': 'Price Discussions',
                'slug': 'price-discussions',
                'description': 'Discuss rental prices and trends'
            },
            {
                'name': 'Roommate Finding',
                'slug': 'roommates',
                'description': 'Find or become a roommate'
            },
        ]

        for cat_data in categories:
            Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )

        self.stdout.write(
            self.style.SUCCESS('Successfully created initial forum data')
        )