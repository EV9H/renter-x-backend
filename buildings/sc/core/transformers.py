from decimal import Decimal
import re
from typing import Any, Callable, Dict
import logging
logger = logging.getLogger(__name__)

class TransformerRegistry:
    def __init__(self):
        self.transformers: Dict[str, Callable] = {
            'extract_string': self._extract_string,
            'extract_bedrooms_from_details': self._extract_bedrooms_from_details,
            'extract_bathrooms_from_details': self._extract_bathrooms_from_details,
            'extract_price_from_details': self._extract_price_from_details,
        }

    def transform(self, transformer_name: str, value: Any) -> Any:
        transformer = self.transformers.get(transformer_name)
        if not transformer:
            raise ValueError(f"Transformer {transformer_name} not found")
        return transformer(value)

    @staticmethod
    def _extract_string(value: str) -> str:
        """Extract clean string value"""
        return value.strip()

    @staticmethod
    def _extract_bedrooms_from_details(value: str) -> Decimal:
        """Extract bedrooms from property details text"""
        try:
            # Handle both "Studio" and "X Bedroom" cases
            if 'Studio' in value:
                return Decimal('0')
            match = re.search(r'(\d+)\s*Bedroom', value)
            if match:
                return Decimal(match.group(1))
            return Decimal('0')
        except Exception as e:
            logger.error(f"Error extracting bedrooms: {str(e)}")
            return Decimal('0')

    @staticmethod
    def _extract_bathrooms_from_details(value: str) -> Decimal:
        """Extract bathrooms from property details text"""
        try:
            match = re.search(r'(\d+\.?\d*)\s*Bathroom', value)
            if match:
                return Decimal(match.group(1))
            return Decimal('1')
        except Exception as e:
            logger.error(f"Error extracting bathrooms: {str(e)}")
            return Decimal('1')

    @staticmethod
    def _extract_price_from_details(value: str) -> Decimal:
        """Extract price from property details text"""
        try:
            # Extract the first price (net price)
            match = re.search(r'\$([0-9,]+)', value)
            if match:
                price_str = match.group(1).replace(',', '')
                return Decimal(price_str)
            return Decimal('0')
        except Exception as e:
            logger.error(f"Error extracting price: {str(e)}")
            return Decimal('0')