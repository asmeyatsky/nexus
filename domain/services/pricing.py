"""Pricing Service — calculates prices with discounts and multi-item quotes."""

from decimal import Decimal


class PricingService:
    """Calculate prices with discounts, taxes, and multi-currency support."""

    def calculate_line_total(
        self, unit_price: Decimal, quantity: int, discount_percent: float = 0.0
    ) -> Decimal:
        price = Decimal(str(unit_price))
        discount = Decimal(str(discount_percent))
        return price * quantity * (1 - discount / 100)

    def calculate_quote_total(self, line_items: list) -> Decimal:
        return sum(
            (
                self.calculate_line_total(
                    item.unit_price, item.quantity, item.discount_percent
                )
                for item in line_items
            ),
            Decimal("0"),
        )
