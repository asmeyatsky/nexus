"""
Industry Value Object

Architectural Intent:
- Value object representing industry classification
- Immutable and validated at creation
- Standardized list of industries for CRM use
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IndustryType(Enum):
    TECHNOLOGY = "technology"
    FINANCIAL_SERVICES = "financial_services"
    HEALTHCARE = "healthcare"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    CONSULTING = "consulting"
    MEDIA = "media"
    TELECOMMUNICATIONS = "telecommunications"
    ENERGY = "energy"
    TRANSPORTATION = "transportation"
    REAL_ESTATE = "real_estate"
    EDUCATION = "education"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    FOOD = "food"
    OTHER = "other"


@dataclass(frozen=True)
class Industry:
    type: IndustryType
    custom_name: Optional[str] = None

    @property
    def display_name(self) -> str:
        if self.custom_name:
            return self.custom_name
        return self.type.value.replace("_", " ").title()

    @staticmethod
    def from_string(value: str) -> "Industry":
        normalized = value.lower().replace(" ", "_")
        for industry_type in IndustryType:
            if industry_type.value == normalized:
                return Industry(type=industry_type)
        return Industry(type=IndustryType.OTHER, custom_name=value)

    @staticmethod
    def technology() -> "Industry":
        return Industry(type=IndustryType.TECHNOLOGY)

    @staticmethod
    def financial_services() -> "Industry":
        return Industry(type=IndustryType.FINANCIAL_SERVICES)

    @staticmethod
    def healthcare() -> "Industry":
        return Industry(type=IndustryType.HEALTHCARE)

    @staticmethod
    def manufacturing() -> "Industry":
        return Industry(type=IndustryType.MANUFACTURING)

    @staticmethod
    def consulting() -> "Industry":
        return Industry(type=IndustryType.CONSULTING)
