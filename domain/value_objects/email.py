"""
Email Value Object

Architectural Intent:
- Value object representing email addresses
- Immutable and validated at creation
- Provides type safety for email addresses
"""

from dataclasses import dataclass
import re


EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@dataclass(frozen=True)
class Email:
    address: str

    def __post_init__(self):
        if not EMAIL_PATTERN.match(self.address):
            raise ValueError(f"Invalid email address: {self.address}")

    @staticmethod
    def create(address: str) -> "Email":
        return Email(address=address.lower())

    def __str__(self) -> str:
        return self.address
