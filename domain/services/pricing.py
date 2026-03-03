"""Pricing Service — calculates prices with discounts and multi-item quotes."""


class PricingService:
    """Calculate prices with discounts, taxes, and multi-currency support."""

    def calculate_line_total(
        self, unit_price: float, quantity: int, discount_percent: float = 0.0
    ) -> float:
        return unit_price * quantity * (1 - discount_percent / 100)

    def calculate_quote_total(self, line_items: list) -> float:
        return sum(
            self.calculate_line_total(
                item.unit_price, item.quantity, item.discount_percent
            )
            for item in line_items
        )
