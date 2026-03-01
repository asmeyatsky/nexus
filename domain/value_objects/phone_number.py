"""
PhoneNumber Value Object

Architectural Intent:
- Value object representing phone numbers
- Immutable and validated at creation
- Stores country code and number separately
"""

from dataclasses import dataclass
from typing import Optional
import re


PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{6,14}$")


@dataclass(frozen=True)
class PhoneNumber:
    country_code: str
    number: str
    extension: Optional[str] = None

    def __post_init__(self):
        full = f"{self.country_code}{self.number}"
        if not PHONE_PATTERN.match(full):
            raise ValueError(f"Invalid phone number: {full}")

    @staticmethod
    def create(phone: str) -> "PhoneNumber":
        cleaned = re.sub(r"[\s\-\(\)]", "", phone)
        if cleaned.startswith("+"):
            code, number = cleaned[1:3], cleaned[3:]
            return PhoneNumber(country_code=f"+{code}", number=number)
        elif len(cleaned) == 10:
            return PhoneNumber(country_code="+1", number=cleaned)
        elif len(cleaned) == 11 and cleaned.startswith("1"):
            return PhoneNumber(country_code="+1", number=cleaned[1:])
        else:
            return PhoneNumber(country_code="+44", number=cleaned)

    @property
    def formatted(self) -> str:
        ext = f" x{self.extension}" if self.extension else ""
        return f"{self.country_code} {self.number}{ext}"

    def __str__(self) -> str:
        return self.formatted
