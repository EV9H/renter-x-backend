from typing import List, Dict
from decimal import Decimal
import asyncio
import yaml
import os
from datetime import datetime
import logging
from asgiref.sync import sync_to_async
from django.db import transaction
from .core.engine import ScraperEngine
from .schemas import ScraperConfig
from buildings.models import Building, Apartment, ApartmentPrice, ScrapingSource, ScrapingRun
from django.utils import timezone

logger = logging.getLogger(__name__)

class ScraperQueue:
    def __init__(self):
        self.configs: List[ScraperConfig] = []
        self.load_configs()

    def load_configs(self):
        """Load all scraper configurations from YAML files"""
        config_dir = os.path.join(os.path.dirname(__file__), 'configs')
        for filename in os.listdir(config_dir):
            if filename.endswith('.yaml'):
                with open(os.path.join(config_dir, filename)) as f:
                    config = yaml.safe_load(f)
                    self.configs.append(ScraperConfig(**config))

    @sync_to_async
    def _create_scraping_run(self, source: ScrapingSource) -> ScrapingRun:
        return ScrapingRun.objects.create(
            source=source,
            start_time=timezone.now(), 
            status=ScrapingRun.RunStatus.IN_PROGRESS
        )

    @sync_to_async
    def _get_or_create_source(self, name: str, url: str) -> ScrapingSource:
        source, _ = ScrapingSource.objects.get_or_create(
            name=name,
            defaults={'base_url': url}
        )
        return source

    @sync_to_async
    def _get_or_create_building(self, building_info: dict) -> Building:
        building, _ = Building.objects.get_or_create(
            name=building_info['name'],
            defaults=building_info
        )
        return building

    @sync_to_async
    def _update_apartment_and_price(self, building: Building, unit_data: dict):
        with transaction.atomic():
            apartment, created = Apartment.objects.update_or_create(
                building=building,
                unit_number=unit_data.unit_number,
                defaults={
                    'floor': unit_data.floor or 1,
                    'bedrooms': unit_data.bedrooms,
                    'bathrooms': unit_data.bathrooms,
                    'area_sqft': unit_data.area_sqft or 0,
                    'apartment_type': unit_data.apartment_type,
                    'features': unit_data.features or {},
                }
            )

            # Check if price has changed
            latest_price = apartment.price_history.order_by('-start_date').first()
            if not latest_price or latest_price.price != unit_data.price:
                ApartmentPrice.objects.create(
                    apartment=apartment,
                    price=unit_data.price,
                    start_date=timezone.now().date(),  # Use timezone-aware date
                    lease_term_months=unit_data.lease_term_months
                )

            return apartment
        
    @sync_to_async
    def _update_scraping_run(self, scraping_run: ScrapingRun, status: str, 
                            items_processed: int = 0, error: str = None):
        scraping_run.status = status
        scraping_run.items_processed = items_processed
        scraping_run.end_time = timezone.now()  
        if error:
            scraping_run.error_log = error
        scraping_run.save()

    # async def run_scraper(self, config: ScraperConfig):
    #     """Run a single scraper and save results"""
    #     try:
    #         # Create scraping source and run
    #         source = await self._get_or_create_source(config.name, config.url)
    #         scraping_run = await self._create_scraping_run(source)

    #         logger.info(f"Starting to scrape: {config.name}")
    #         logger.info(f"URL: {config.url}")

    #         # Get or create building
    #         building = await self._get_or_create_building(config.building_info)
    #         logger.info(f"Building: {building.name}")

    #         # Run scraper
    #         engine = ScraperEngine(config.dict())
    #         units = await engine.scrape()
            
    #         logger.info(f"Found {len(units)} units")

    #         # Update apartments and prices
    #         for i, unit in enumerate(units, 1):
    #             await self._update_apartment_and_price(building, unit)
    #             if i % 5 == 0:  # Log progress every 5 units
    #                 logger.info(f"Processed {i}/{len(units)} units")

    #         # Update scraping run status
    #         await self._update_scraping_run(
    #             scraping_run, 
    #             ScrapingRun.RunStatus.COMPLETED,
    #             len(units)
    #         )

    #         logger.info(f"Successfully completed scraping {config.name}")

    #     except Exception as e:
    #         logger.error(f"Error running scraper for {config.name}: {str(e)}")
    #         if 'scraping_run' in locals():
    #             await self._update_scraping_run(
    #                 scraping_run,
    #                 ScrapingRun.RunStatus.FAILED,
    #                 error=str(e)
    #             )
    #         raise
    
    @sync_to_async
    def _process_unit_data(self, building: Building, unit_data: Dict) -> None:
        """Process and save unit data to database"""
        try:
            with transaction.atomic():
                # Ensure we have the minimum required data
                required_fields = {'unit_number', 'bedrooms', 'bathrooms', 'price'}
                if not all(field in unit_data for field in required_fields):
                    missing = required_fields - set(unit_data.keys())
                    raise ValueError(f"Missing required fields: {missing}")
                    
                # Clean up unit number
                unit_number = unit_data['unit_number']
                
                # Default values for required fields
                defaults = {
                    'floor': self._extract_floor(unit_number),
                    'bedrooms': unit_data['bedrooms'],
                    'bathrooms': unit_data['bathrooms'],
                    'area_sqft': unit_data.get('area_sqft', 0),  # Default to 0 if missing
                    'apartment_type': self._get_apartment_type(unit_data['bedrooms']),
                    'status': 'available',
                    'features': unit_data.get('features', {}),
                }

                # logger.info(f"Creating/updating apartment {unit_number} with data: {defaults}")

                # Get or create apartment
                apartment, created = Apartment.objects.update_or_create(
                    building=building,
                    unit_number=unit_number,
                    defaults=defaults
                )

                # Add price history
                latest_price = apartment.price_history.order_by('-start_date').first()
                if not latest_price or latest_price.price != unit_data['price']:
                    ApartmentPrice.objects.create(
                        apartment=apartment,
                        price=unit_data['price'],
                        start_date=timezone.now().date(),
                        lease_term_months=12,
                    )

                # logger.info(f"{'Created' if created else 'Updated'} apartment {unit_number}")

        except Exception as e:
            # logger.error(f"Error processing unit data: {str(e)}")
            # logger.error(f"Unit data: {unit_data}")
            raise

    @staticmethod
    def _extract_floor(unit_number: str) -> int:
        """Extract floor number from unit number"""
        try:
            if 'PH' in unit_number:
                return 99  # Penthouse floor
            # Try to extract numeric portion from unit number
            floor = ''.join(filter(str.isdigit, unit_number.split('-')[0]))
            return int(floor[:2])  # First two digits usually represent floor
        except Exception:
            return 1

    @staticmethod
    def _get_apartment_type(bedrooms: Decimal) -> str:
        """Convert number of bedrooms to apartment type"""
        if bedrooms == 0:
            return 'Studio'
        return f'{int(bedrooms)}B{int(bedrooms)}B'

    async def run_scraper(self, config: ScraperConfig):
        """Run a single scraper and save results"""
        try:
            logger.info("Queue# Get or create source")
            source = await sync_to_async(ScrapingSource.objects.get_or_create)(
                name=config.name,
                defaults={'base_url': config.url}
            )
            source = source[0]  

            logger.info("Queue# Create scraping run")
            scraping_run = await sync_to_async(ScrapingRun.objects.create)(
                source=source,
                start_time=timezone.now(),
                status=ScrapingRun.RunStatus.IN_PROGRESS
            )

            logger.info("Queue# Get or create building")
            building = await sync_to_async(Building.objects.get_or_create)(
                name=config.building_info['name'],
                defaults=config.building_info
            )
            building = building[0]  

            logger.info("Queue# Run scraper")
            engine = ScraperEngine(config.dict())
            units = await engine.scrape()

            logger.info("Queue# Process each unit")
            for unit in units:
                await self._process_unit_data(building, unit)
                
            logger.info("Queue# Update scraping run status")
            await sync_to_async(self._update_scraping_run)(
                scraping_run,
                ScrapingRun.RunStatus.COMPLETED,
                len(units)
            )


        except Exception as e:
            # logger.error(f"Error running scraper for {config.name}: {str(e)}")
            if 'scraping_run' in locals():
                await sync_to_async(self._update_scraping_run)(
                    scraping_run,
                    ScrapingRun.RunStatus.FAILED,
                    error=str(e)
                )
            raise

    @staticmethod
    def _update_scraping_run(scraping_run: ScrapingRun, status: str, 
                            items_processed: int = 0, error: str = None) -> None:
        """Update scraping run status"""
        scraping_run.status = status
        scraping_run.items_processed = items_processed
        scraping_run.end_time = timezone.now()
        if error:
            scraping_run.error_log = error
        scraping_run.save()

    async def process_queue(self):
        """Process all scrapers in the queue"""
        
        tasks = []
        for config in self.configs:
            tasks.append(self.run_scraper(config))
        
        await asyncio.gather(*tasks)