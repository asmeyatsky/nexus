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
            digits = cleaned[1:]
            # Try 1, 2, and 3-digit country codes to find a valid parse
            for code_len in (1, 2, 3):
                if len(digits) > code_len:
                    code = digits[:code_len]
                    number = digits[code_len:]
                    try:
                        return PhoneNumber(country_code=f"+{code}", number=number)
                    except ValueError:
                        continue
            raise ValueError(f"Invalid phone number: {cleaned}")
        elif len(cleaned) == 10:
            return PhoneNumber(country_code="+1", number=cleaned)
        elif len(cleaned) == 11 and cleaned.startswith("1"):
            return PhoneNumber(country_code="+1", number=cleaned[1:])
        else:
            raise ValueError(
                f"Cannot parse phone number: {phone}. Provide in E.164 format (+<country_code><number>)."
            )

    @property
    def formatted(self) -> str:
        ext = f" x{self.extension}" if self.extension else ""
        return f"{self.country_code} {self.number}{ext}"

    def __str__(self) -> str:
        return self.formatted
