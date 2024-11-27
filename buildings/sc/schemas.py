from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Dict, Optional
from datetime import date

class ScrapedUnit(BaseModel):
    unit_number: str
    floor: int
    bedrooms: Decimal
    bathrooms: Decimal
    area_sqft: int
    price: Decimal
    apartment_type: str
    features: Dict[str, bool] = Field(default_factory=dict)
    availability_date: Optional[date] = None
    lease_term_months: int = 12

class ScraperConfig(BaseModel):
    name: str
    url: str
    parser_type: str = 'html'
    selector_type: str = 'class'
    building_info: Dict
    selectors: Dict
    transformers: Dict = Field(
        default_factory=lambda: {
            'price': 'extract_price',
            'bedrooms': 'extract_bedrooms',
            'bathrooms': 'extract_bathrooms',
            'area_sqft': 'extract_sqft',
            'floor': 'extract_floor'
        }
    )
    headers: Optional[Dict] = None