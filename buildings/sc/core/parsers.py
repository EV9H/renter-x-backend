from abc import ABC, abstractmethod
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> Any:
        pass
    
    @abstractmethod
    async def parse(self, data: Any, selectors: Dict) -> List[Dict]:
        pass

class HTMLParser(BaseParser):
    async def fetch(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()

    async def parse(self, html: str, selectors: Dict) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        units = []
        
        # Find all unit elements
        unit_elements = soup.select(selectors['unit_list'])
        
        for element in unit_elements:
            unit_data = {}
            # Extract data using selectors
            for field, selector in selectors['unit_data'].items():
                field_element = element.select_one(selector)
                if field_element:
                    unit_data[field] = field_element.text.strip()
            
            if unit_data:
                units.append(unit_data)
        
        return units

class JSParser(BaseParser):
    async def fetch(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            # Wait for content to load
            await page.wait_for_selector(selectors['unit_list'])
            content = await page.content()
            await browser.close()
            return content

    async def parse(self, html: str, selectors: Dict) -> List[Dict]:
        # Reuse HTML parser's parse method
        return await HTMLParser().parse(html, selectors)

class APIParser(BaseParser):
    async def fetch(self, url: str) -> Dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    async def parse(self, data: Dict, mapping: Dict) -> List[Dict]:
        units = []
        raw_units = data
        for path in mapping['unit_list'].split('.'):
            raw_units = raw_units.get(path, [])
        
        for raw_unit in raw_units:
            unit_data = {}
            for field, path in mapping['unit_data'].items():
                value = raw_unit
                for key in path.split('.'):
                    value = value.get(key, '')
                unit_data[field] = value
            units.append(unit_data)
        
        return units

def get_parser(parser_type: str) -> BaseParser:
    parsers = {
        'html': HTMLParser(),
        'js': JSParser(),
        'api': APIParser()
    }
    return parsers.get(parser_type, HTMLParser())