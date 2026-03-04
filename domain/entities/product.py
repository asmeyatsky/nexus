"""
Product & Price Book Entities

Architectural Intent:
- Product catalog management
- Price book support for multi-currency pricing
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from decimal import Decimal


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    code: str
    description: str
    family: str
    unit_price: Decimal
    currency: str
    is_active: bool
    org_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        id: str,
        name: str,
        code: str,
        description: str,
        family: str,
        unit_price: Decimal,
        currency: str,
        org_id: str,
    ) -> "Product":
        return Product(
            id=id,
            name=name,
            code=code,
            description=description,
            family=family,
            unit_price=unit_price,
            currency=currency,
            is_active=True,
            org_id=org_id,
        )


@dataclass(frozen=True)
class PriceBookEntry:
    id: str
    product_id: str
    price_book_id: str
    unit_price: Decimal
    currency: str
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
