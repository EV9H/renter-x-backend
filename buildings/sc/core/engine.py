from typing import Dict, Any, List, Optional
import logging
from .parsers import get_parser
from .transformers import TransformerRegistry
from .monitors import ScraperMonitor
from ..schemas import ScrapedUnit
import aiohttp
logger = logging.getLogger(__name__)

from playwright.async_api import async_playwright
import asyncio
import random
from bs4 import BeautifulSoup


class ScraperEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.monitor = ScraperMonitor()
        self.transformers = TransformerRegistry()
        self.selectors = config['selectors']  # Extract selectors from config
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]

    async def _wait_for_angular(self, page):
        """Wait for Angular to finish loading"""
        try:
            # Wait for ng-scope to be present (indicates Angular has initialized)
            await page.wait_for_selector('.ng-scope', timeout=20000)
            
            # Wait additional time for potential data loading
            await asyncio.sleep(2)
            
            # Check if any loading indicators are present and wait for them to disappear
            loading_indicators = await page.query_selector_all('.loading, .spinner')
            for indicator in loading_indicators:
                await indicator.wait_for_element_state('hidden')
                
            logger.info("Angular app appears to be fully loaded")
            return True
        except Exception as e:
            logger.error(f"Error waiting for Angular: {str(e)}")
            return False

    async def scrape(self) -> List[Dict]:
        """Main scraping method"""
        try:
            self.monitor.start_scrape(self.config['name'])
            
            # Fetch webpage content
            html_content = await self._fetch_page_with_playwright(self.config['url'])
            if not html_content:
                raise Exception("Failed to fetch webpage content")

            # Parse the content
            units = await self._parse_content(html_content)
            
            self.monitor.end_scrape(self.config['name'], len(units))
            return units

        except Exception as e:
            self.monitor.record_error(self.config['name'], str(e))
            logger.error(f"Error in scraping process: {str(e)}")
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
                    await asyncio.sleep(1)

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

    # async def _parse_content(self, html_content: str) -> List[Dict]:
    #     try:
    #         soup = BeautifulSoup(html_content, 'html.parser')
    #         units = []

    #         unit_containers = soup.select(self.selectors['unit_list'])
    #         logger.info(f"Found {len(unit_containers)} potential units")
    #         for container in unit_containers:
    #             try:
    #                 unit_data = {}
    #                 required_fields = {'unit_number', 'bedrooms', 'bathrooms', 'price'}
                    
    #                 # Extract raw text first
    #                 for field, selector in self.selectors['unit_data'].items():
    #                     element = container.select_one(selector)
    #                     if element:
    #                         raw_text = element.text.strip()
    #                         logger.info(raw_text)
    #                         # Clean the text directly
    #                         unit_data[field] = ' '.join(raw_text.split())
                    
    #                 # Transform the data
    #                 transformed_data = {}
    #                 for field, transformer_name in self.config.get('transformers', {}).items():
    #                     if field in unit_data:
    #                         try:
    #                             transformed_data[field] = self.transformers.transform(
    #                                 transformer_name, 
    #                                 unit_data[field]
    #                             )
    #                         except Exception as e:
    #                             logger.error(f"Error transforming {field}: {str(e)}")
    #                             continue
                    
    #                 # Add unit number directly from raw data
    #                 if 'unit_number' in unit_data:
    #                     transformed_data['unit_number'] = unit_data['unit_number'].replace('Residence', '').strip()
                    
    #                 # Validate the transformed data
    #                 if all(field in transformed_data for field in required_fields):
    #                     logger.info(f"Successfully transformed unit: {transformed_data}")
    #                     units.append(transformed_data)
    #                 else:
    #                     missing = required_fields - set(transformed_data.keys())
    #                     logger.warning(f"Missing required fields {missing} in transformed data: {transformed_data}")
    #                     logger.warning(f"Original unit data: {unit_data}")

    #             except Exception as e:
    #                 logger.error(f"Error parsing unit container: {str(e)}", exc_info=True)
    #                 continue

    #         return units

    #     except Exception as e:
    #         logger.error(f"Error parsing content: {str(e)}", exc_info=True)
    #         raise
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
                        unit_data['unit_number'] = container.get('data-name', '').strip()
                        unit_data['bedrooms'] = container.get('data-rooms', '').strip()
                        unit_data['bathrooms'] = container.get('data-bath', '').strip()
                        unit_data['price'] = container.get('data-rent', '').strip()

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
                                logger.info(raw_text)
                                # Clean the text directly
                                unit_data[field] = ' '.join(raw_text.split())
                        
                        # Transform the data
                        transformed_data = {}
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
    
    
# Add explicit print statements for debugging
logger.info("Loaded scraper engine")
