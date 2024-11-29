from datetime import date
from decimal import Decimal
import re
from typing import Any, Callable, Dict, Optional
import logging
logger = logging.getLogger(__name__)

class TransformerRegistry:
    def __init__(self):
        self.transformers: Dict[str, Callable] = {
            'extract_string': self._extract_string,
            'extract_bedrooms_from_details': self._extract_bedrooms_from_details,
            'extract_bathrooms_from_details': self._extract_bathrooms_from_details,
            'extract_price_from_details': self._extract_price_from_details,
            'extract_bedrooms': self._extract_bedrooms,  
            'extract_bathrooms': self._extract_bathrooms,  
            'extract_price': self._extract_price,  
            'clean_text': self._extract_clean_text,
            'transform_date': self._transform_date
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
        
    @staticmethod
    def _extract_bedrooms(value: str) -> Decimal:
        """
        Extract bedrooms from property details text.
        Supports formats like:
        - "2 Bedrooms"
        - "2 bed"
        - "Studio"
        - "2"
        """
        try:
            # Handle Studio case
            if 'Studio' in value:
                return Decimal('0')
                
            # Handle direct numeric input
            if value.replace('.', '').isdigit():
                return Decimal(value)
            
            # Look for bedroom/bed mentions
            patterns = [
                r'(\d+)\s*Bedroom',
                r'(\d+)\s*bed',
                r'(\d+)\s*Bd'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, value, re.IGNORECASE)
                if match:
                    return Decimal(match.group(1))
            
            # If no matches found, try to extract any number
            numbers = re.findall(r'\d+', value)
            if numbers:
                return Decimal(numbers[0])
                
            return Decimal('0')  # Default value
            
        except Exception as e:
            logger.error(f"Error extracting bedrooms: {str(e)}")
            return Decimal('0')

    @staticmethod
    def _extract_bathrooms(value: str) -> Decimal:
        """
        Extract bathrooms from property details text.
        Supports formats like:
        - "2 Bathrooms"
        - "2 bath"
        - "2.5 Bathroom"
        - "2"
        """
        try:
            # Handle direct numeric input
            if value.replace('.', '').isdigit():
                return Decimal(value)
            
            # Look for bathroom/bath mentions
            patterns = [
                r'(\d+\.?\d*)\s*Bathroom',
                r'(\d+\.?\d*)\s*bath',
                r'(\d+\.?\d*)\s*Ba'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, value, re.IGNORECASE)
                if match:
                    return Decimal(match.group(1))
            
            # If no matches found, try to extract any number
            numbers = re.findall(r'\d+\.?\d*', value)
            if numbers:
                return Decimal(numbers[0])
                
            return Decimal('1')  # Default value
            
        except Exception as e:
            logger.error(f"Error extracting bathrooms: {str(e)}")
            return Decimal('1')

    @staticmethod
    def _extract_price(value: str) -> Decimal:
        """Extract price from price text"""
        try:
            match = re.search(r'\$([0-9,]+)', value)
            if match:
                return Decimal(match.group(1).replace(',', ''))
            return Decimal('0')
        except:
            return Decimal('0')
        
    @staticmethod
    def _extract_clean_text(value: str) -> str:
        """Clean text by removing excess whitespace and newlines"""
        return ' '.join(value.split())
    
    @staticmethod
    def _transform_date(value: str) -> Optional[date]:
        """Transform date text into date object"""
        try:
            from datetime import datetime
            return datetime.strptime(value.strip(), '%B %d, %Y').date()
        except Exception:
            return None