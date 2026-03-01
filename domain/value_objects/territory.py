"""
Territory Value Object

Architectural Intent:
- Value object representing geographic territory
- Immutable and validated at creation
- Supports hierarchical territory structures
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Territory:
    region: str
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None

    @property
    def display_name(self) -> str:
        parts = []
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country:
            parts.append(self.country)
        if not parts:
            parts.append(self.region)
        return ", ".join(parts)

    @staticmethod
    def emea() -> "Territory":
        return Territory(region="EMEA")

    @staticmethod
    def apac() -> "Territory":
        return Territory(region="APAC")

    @staticmethod
    def americas() -> "Territory":
        return Territory(region="Americas")

    @staticmethod
    def uk() -> "Territory":
        return Territory(region="EMEA", country="United Kingdom")

    @staticmethod
    def us() -> "Territory":
        return Territory(region="Americas", country="United States")

    @staticmethod
    def india() -> "Territory":
        return Territory(region="APAC", country="India")

    @staticmethod
    def uae() -> "Territory":
        return Territory(region="EMEA", country="UAE")
