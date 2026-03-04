"""
Money Value Object

Architectural Intent:
- Value object representing monetary amounts
- Immutable with currency validation
- Provides type-safe arithmetic operations
"""

from dataclasses import dataclass
from decimal import Decimal


CURRENCY_CODES = {"USD", "GBP", "EUR", "INR", "AED"}


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self):
        if self.currency not in CURRENCY_CODES:
            raise ValueError(f"Unsupported currency: {self.currency}")

    @staticmethod
    def from_float(amount: float, currency: str = "USD") -> "Money":
        return Money(Decimal(str(amount)), currency.upper())

    @staticmethod
    def zero(currency: str = "USD") -> "Money":
        return Money(Decimal("0"), currency.upper())

    @property
    def amount_float(self) -> float:
        return float(self.amount)

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot subtract money with different currencies")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, multiplier: Decimal) -> "Money":
        return Money(self.amount * multiplier, self.currency)

    def __gt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError("Cannot compare money with different currencies")
        return self.amount > other.amount

    def __radd__(self, other):
        if other == 0:
            return self
        return NotImplemented

    def __lt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError("Cannot compare money with different currencies")
        return self.amount < other.amount

    def __ge__(self, other: "Money") -> bool:
        return self.__gt__(other) or self == other

    def __le__(self, other: "Money") -> bool:
        return self.__lt__(other) or self == other

    def format(self) -> str:
        symbols = {"USD": "$", "GBP": "£", "EUR": "€", "INR": "₹", "AED": "د.إ"}
        symbol = symbols.get(self.currency, self.currency)
        return f"{symbol}{self.amount:,.2f}"
