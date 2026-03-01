"""
Domain Value Objects

Architectural Intent:
- Immutable value objects representing domain concepts
- No identity, compared by value
- Validated at creation
"""

from domain.value_objects.industry import Industry, IndustryType
from domain.value_objects.territory import Territory
from domain.value_objects.money import Money
from domain.value_objects.email import Email
from domain.value_objects.phone_number import PhoneNumber

__all__ = [
    "Industry",
    "IndustryType",
    "Territory",
    "Money",
    "Email",
    "PhoneNumber",
]
