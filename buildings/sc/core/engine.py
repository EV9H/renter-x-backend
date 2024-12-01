from typing import Dict, Any, List, Optional, Set
from decimal import Decimal
import logging
from .parsers import get_parser
from .transformers import TransformerRegistry
from .monitors import ScraperMonitor
from ..schemas import ScrapedUnit
import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio
from django.utils import timezone
from django.db import transaction
from ...models import (
    Building, Apartment, ApartmentPrice, ScrapingSource, 
    ScrapingRun, PriceChange
)
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class ScraperEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.monitor = ScraperMonitor()
        self.transformers = TransformerRegistry()
        self.selectors = config['selectors']
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]

    @staticmethod
    def _get_apartment_type(bedrooms: Decimal) -> str:
        """Convert number of bedrooms to apartment type"""
        if bedrooms == 0:
            return 'Studio'
        return f'{int(bedrooms)}B{int(bedrooms)}B'
    
    # async def _wait_for_angular(self, page):
    #     """Wait for Angular to finish loading"""
    #     try:
    #         # Wait for ng-scope to be present (indicates Angular has initialized)
    #         await page.wait_for_selector('.ng-scope', timeout=20000)
            
    #         # Wait additional time for potential data loading
    #         await asyncio.sleep(2)
            
    #         # Check if any loading indicators are present and wait for them to disappear
    #         loading_indicators = await page.query_selector_all('.loading, .spinner')
    #         for indicator in loading_indicators:
    #             await indicator.wait_for_element_state('hidden')
                
    #         logger.info("Angular app appears to be fully loaded")
    #         return True
    #     except Exception as e:
    #         logger.error(f"Error waiting for Angular: {str(e)}")
    #         return False

    async def scrape(self) -> List[Dict]:
        """Main scraping method with enhanced tracking"""
        try:
            logger.info("# Initialize scraping run")
            source, _ = await sync_to_async(self._db_get_or_create_source)()
            scraping_run = await sync_to_async(self._db_create_scraping_run)(source)
            
            logger.info("# Get building")
            building, _ = await sync_to_async(self._db_get_or_create_building)()
            
            logger.info("# Fetch and parse content")
            html_content = await self._fetch_page_with_playwright(self.config['url'])
            if not html_content:
                raise Exception("Failed to fetch webpage content")

            logger.info("# Parse units")
            current_units = await self._parse_content(html_content)
            
            logger.info("# Process units and track changes")
            stored_units = await sync_to_async(self._db_get_stored_units)(building)
            current_unit_numbers = set()
            
            logger.info("# Process current units")
            for unit_data in current_units:
                current_unit_numbers.add(unit_data['unit_number'])
                await sync_to_async(self._db_process_single_unit)(building, unit_data, scraping_run)
            
            logger.info("# Handle removed units")
            removed_units = stored_units - current_unit_numbers
            if removed_units:
                await sync_to_async(self._db_handle_removed_units)(building, removed_units)
            
            logger.info("# Update scraping run status")
            await sync_to_async(self._db_update_scraping_run)(
                scraping_run,
                'completed',
                len(current_units)
            )
            
            return current_units

        except Exception as e:
            logger.error(f"Error in scraping process: {str(e)}")
            if 'scraping_run' in locals():
                await sync_to_async(self._db_update_scraping_run)(
                    scraping_run,
                    'failed',
                    error=str(e)
                )
            return []

    async def _fetch_page(self, url: str) -> str:
        """Fetch webpage content"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        raise Exception(f"HTTP {response.status}: Failed to fetch {url}")
        except Exception as e:
            logger.error(f"Error fetching page {url}: {str(e)}")
            raise

    async def _fetch_page_with_playwright(self, url: str) -> Optional[str]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.user_agents[0],
                viewport={'width': 1920, 'height': 1080}
            )

            try:
                page = await context.new_page()
                logger.info(f"Navigating to {url}")
                await page.goto(url, wait_until='networkidle', timeout=60000)

                # Scroll to load all content
                for _ in range(10):
                    await page.evaluate("window.scrollBy(0, 500);")
                    await asyncio.sleep(0.5)

                # Wait for the elements to load
                unit_list_selector = self.selectors['unit_list']
                elements = await page.query_selector_all(unit_list_selector)
                if not elements:
                    raise Exception("No units found on the page")
                logger.info(f"Found {len(elements)} units")

                # Capture content
                content = await page.content()
                return content

            except Exception as e:
                logger.error(f"Error during page fetch: {str(e)}")
                await page.screenshot(path="error_screenshot.png")
                raise

            finally:
                await browser.close()

    async def _parse_content(self, html_content: str) -> List[Dict]:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            units = []

            # Select all unit containers
            unit_containers = soup.select(self.selectors['unit_list'])
            logger.info(f"Found {len(unit_containers)} potential units")

            if self.config.get('selector_type') == 'attribute':
                logger.info("Using attribute selector logic")
                for container in unit_containers:
                    try:
                        unit_data = {}
                        required_fields = {'unit_number', 'bedrooms', 'bathrooms', 'price'}

                        # Extract attributes directly from the container
                        
                        unit_data['unit_number'] = container.get(self.selectors['unit_data']['unit_number'], '').strip()
                        unit_data['bedrooms'] = container.get(self.selectors['unit_data']['bedrooms'], '').strip()
                        unit_data['bathrooms'] = container.get(self.selectors['unit_data']['bathrooms'], '').strip()
                        unit_data['price'] = container.get(self.selectors['unit_data']['price'], '').strip()

                        logger.debug(f"Extracted unit data: {unit_data}")

                        # Validate the required fields
                        if all(field in unit_data and unit_data[field] for field in required_fields):
                            logger.info(f"Successfully retrieve unit: {unit_data}")
                            units.append(unit_data)
                        else:
                            logger.warning(f"Missing fields in unit data: {unit_data}")

                    except Exception as e:
                        logger.error(f"Error parsing container: {str(e)}", exc_info=True)
                        continue
            else:
                logger.info("Using default selector logic")
                for container in unit_containers:
                    try:
                        unit_data = {}
                        required_fields = {'unit_number', 'bedrooms', 'bathrooms', 'price'}
                        
                        # Extract raw text first
                        for field, selector in self.selectors['unit_data'].items():
                            element = container.select_one(selector)
                            if element:
                                raw_text = element.text.strip()
                                # Clean the text directly
                                unit_data[field] = ' '.join(raw_text.split())
                        
                        # Transform the data
                        transformed_data = {}
                        # SPECIAL CASE: bedroom and bathroom is in the same field
                        if "bedrooms_bathrooms" in unit_data.keys():
                            bb_split = unit_data["bedrooms_bathrooms"].split(self.config['spliter_for_combined_bb'])
                            if len(bb_split) > 1: # NON-studio
                                unit_data['bedrooms'] = bb_split[0]
                                unit_data['bathrooms'] = bb_split[1]
                            else: # studio
                                unit_data['bathrooms'] = "1 Bathroom"
                                unit_data['bedrooms'] = bb_split[0]
                            unit_data.pop('bedrooms_bathrooms')
                        print("BEFORE TRANSFORMER", unit_data)
                        for field, transformer_name in self.config.get('transformers', {}).items():
                            if field in unit_data:
                                try:
                                    transformed_data[field] = self.transformers.transform(
                                        transformer_name, 
                                        unit_data[field]
                                    )
                                except Exception as e:
                                    logger.error(f"Error transforming {field}: {str(e)}")
                                    continue
                        print("AFTER TRANSFORMER", unit_data)
                        
                        # Add unit number directly from raw data
                        if 'unit_number' in unit_data:
                            transformed_data['unit_number'] = unit_data['unit_number'].replace('Residence', '').strip()
                        
                        # Validate the transformed data
                        if all(field in transformed_data for field in required_fields):
                            logger.info(f"Successfully transformed unit: {transformed_data}")
                            units.append(transformed_data)
                        else:
                            missing = required_fields - set(transformed_data.keys())
                            logger.warning(f"Missing required fields {missing} in transformed data: {transformed_data}")
                            logger.warning(f"Original unit data: {unit_data}")

                    except Exception as e:
                        logger.error(f"Error parsing unit container: {str(e)}", exc_info=True)
                        continue
            return units
        except Exception as e:
            logger.error(f"Error parsing content: {str(e)}", exc_info=True)
            return []


    def _safe_extract(self, container, selector: str) -> str:
        """Safely extract text from element"""
        element = container.select_one(selector)
        return element.text.strip() if element else ''

    def _extract_floor(self, container) -> int:
        """Extract floor number"""
        floor_text = self._safe_extract(container, '.floor-number')
        try:
            return int(''.join(filter(str.isdigit, floor_text)))
        except ValueError:
            return 1

    def _extract_bedrooms(self, container) -> float:
        """Extract number of bedrooms"""
        bed_text = self._safe_extract(container, '.bedrooms')
        if 'studio' in bed_text.lower():
            return 0
        try:
            return float(bed_text[0])
        except (ValueError, IndexError):
            return 0

    def _extract_bathrooms(self, container) -> float:
        """Extract number of bathrooms"""
        bath_text = self._safe_extract(container, '.bathrooms')
        try:
            return float(bath_text.split()[0])
        except (ValueError, IndexError):
            return 1

    def _extract_area(self, container) -> int:
        """Extract square footage"""
        area_text = self._safe_extract(container, '.square-feet')
        try:
            return int(''.join(filter(str.isdigit, area_text)))
        except ValueError:
            return 0

    def _extract_price(self, container) -> float:
        """Extract price"""
        price_text = self._safe_extract(container, '.price')
        try:
            return float(''.join(filter(str.isdigit, price_text)))
        except ValueError:
            return 0

    def _extract_features(self, container) -> Dict:
        """Extract unit features"""
        features_text = self._safe_extract(container, '.features')
        return {
            feature.strip().lower(): True
            for feature in features_text.split(',')
            if feature.strip()
        }

    def _is_valid_unit(self, unit: Dict) -> bool:
        """Validate unit data"""
        return all([
            unit['unit_number'],
            unit['area_sqft'] > 0,
            unit['price'] > 0
        ])
    def _db_get_or_create_source(self):
        """Sync version of get or create source"""
        return ScrapingSource.objects.get_or_create(
            name=self.config['name'],
            defaults={'base_url': self.config['url']}
        )
    
    def _db_create_scraping_run(self, source):
        """Sync version of create scraping run"""
        return ScrapingRun.objects.create(
            source=source,
            start_time=timezone.now(),
            status='in_progress'
        )

    def _db_get_or_create_building(self):
        """Sync version of get or create building"""
        return Building.objects.get_or_create(
            name=self.config['building_info']['name'],
            defaults=self.config['building_info']
        )

    def _db_get_stored_units(self, building):
        """Sync version of get stored units"""
        return set(Apartment.objects.filter(
            building=building
        ).values_list('unit_number', flat=True))

    def _db_process_single_unit(self, building, unit_data, scraping_run):
        """Sync version of process single unit"""
        with transaction.atomic():
            apartment, created = Apartment.objects.get_or_create(
                building=building,
                unit_number=unit_data['unit_number'],
                defaults={
                    'floor': unit_data.get('floor', 1),
                    'bedrooms': Decimal(str(unit_data['bedrooms'])),
                    'bathrooms': Decimal(str(unit_data['bathrooms'])),
                    'area_sqft': unit_data.get('area_sqft', 0),
                    'apartment_type': self._get_apartment_type(Decimal(str(unit_data['bedrooms']))),
                    'status': 'available'
                }
            )

            latest_price = ApartmentPrice.objects.filter(
                apartment=apartment
            ).order_by('-start_date').first()

            current_price = Decimal(str(unit_data['price']))
            
            if not latest_price or latest_price.price != current_price:
                ApartmentPrice.objects.create(
                    apartment=apartment,
                    price=current_price,
                    start_date=timezone.now().date(),
                    lease_term_months=unit_data.get('lease_term_months', 12)
                )
                
                if not created and latest_price:
                    PriceChange.objects.create(
                        apartment=apartment,
                        old_price=latest_price.price,
                        new_price=current_price,
                        scraping_run=scraping_run
                    )

    def _db_handle_removed_units(self, building, removed_units):
        """Sync version of handle removed units"""
        with transaction.atomic():
            Apartment.objects.filter(
                building=building,
                unit_number__in=removed_units,
                status='available'
            ).update(
                status='unavailable',
                updated_at=timezone.now()
            )

    def _db_update_scraping_run(self, scraping_run, status, items_processed=0, error=None):
        """Sync version of update scraping run"""
        scraping_run.status = status
        scraping_run.items_processed = items_processed
        scraping_run.end_time = timezone.now()
        if error:
            scraping_run.error_log = error
        scraping_run.save()
# Add explicit print statements for debugging
logger.info("Loaded scraper engine")
