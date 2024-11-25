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
        """Fetch page using Playwright with Angular support"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.user_agents[0],
                viewport={'width': 1920, 'height': 1080}
            )
            
            try:
                page = await context.new_page()
                
                # Enable detailed logging
                page.on('console', lambda msg: logger.debug(f'Browser console: {msg.text}'))
                page.on('pageerror', lambda err: logger.error(f'Browser error: {err}'))
                
                # Navigate to the page
                logger.info(f"Navigating to {url}")
                await page.goto(url, wait_until='networkidle')
                
                # Wait for Angular
                logger.info("Waiting for Angular to load...")
                await self._wait_for_angular(page)
                
                # Wait for the specific elements we're interested in
                logger.info("Waiting for apartment listings...")
                try:
                    await page.wait_for_selector('.availibility-box', timeout=10000)
                    logger.info("Found availability boxes")
                except Exception as e:
                    logger.warning(f"Timeout waiting for availability boxes: {str(e)}")
                
                # Save page state for debugging
                await page.screenshot(path='debug_screenshot.png')
                
                # Get the page content
                content = await page.content()
                
                # Save HTML for debugging
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("Successfully retrieved page content")
                return content

            except Exception as e:
                logger.error(f"Error during page fetch: {str(e)}")
                await page.screenshot(path='error_screenshot.png')
                raise
            
            finally:
                await context.close()
                await browser.close() 

    async def _parse_content(self, html_content: str) -> List[Dict]:
        """Parse HTML content to extract unit information"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            units = []

            # Find all unit containers
            unit_containers = soup.select('.availibility-box')
            logger.info(f"Found {len(unit_containers)} potential units")

            # Floor plan size reference data (typical sizes based on bedrooms)
            DEFAULT_SIZES = {
                0: 500,  # Studio
                1: 700,  # 1 bedroom
                2: 1000,  # 2 bedrooms
                3: 1400,  # 3 bedrooms
                4: 1800   # 4 bedrooms
            }

            for container in unit_containers:
                try:
                    # Extract modal content for additional details
                    unit_number = container.select_one('.box-title').text.strip()
                    modal_link = container.select_one('[data-target="#availabilityModal"]')
                    area_sqft = None

                    # Try to find square footage in modal content
                    if modal_link:
                        modal_content = container.find_next('.modal-body')
                        if modal_content:
                            # Look for square footage in the description
                            description = modal_content.text.lower()
                            sqft_match = re.search(r'(\d+)\s*sq\s*ft', description)
                            if sqft_match:
                                area_sqft = int(sqft_match.group(1))

                    # Extract other details
                    tower = container.select_one('.tower-title').text.strip()
                    details_elems = container.select('.property-details')
                    details_texts = [elem.text.strip() for elem in details_elems]

                    # Process details
                    bedrooms = bathrooms = price = None
                    for text in details_texts:
                        if 'Bedroom' in text:
                            bedrooms = self.transformers.transform('extract_bedrooms_from_details', text)
                        if 'Bathroom' in text:
                            bathrooms = self.transformers.transform('extract_bathrooms_from_details', text)
                        if '$' in text:
                            price = self.transformers.transform('extract_price_from_details', text)

                    # Use default size if we couldn't find the actual size
                    if area_sqft is None and bedrooms is not None:
                        area_sqft = DEFAULT_SIZES.get(int(bedrooms), 1000)
                        logger.warning(f"Using default size {area_sqft} for unit {unit_number}")

                    unit = {
                        'tower': tower,
                        'unit_number': unit_number,
                        'bedrooms': bedrooms,
                        'bathrooms': bathrooms,
                        'price': price,
                        'area_sqft': area_sqft,
                        'features': self._extract_features(container),
                    }

                    if all(v is not None for v in [bedrooms, bathrooms, price, area_sqft]):
                        units.append(unit)
                        logger.info(f"Successfully parsed unit: {unit}")
                    else:
                        logger.warning(f"Incomplete unit data: {unit}")

                except Exception as e:
                    logger.warning(f"Error parsing unit container: {str(e)}")
                    continue

            return units

        except Exception as e:
            logger.error(f"Error parsing content: {str(e)}")
            raise

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
