"""Deduplication Service — detect duplicate records using fuzzy matching."""

from typing import List
from domain.entities import Account


class DeduplicationService:
    """Detect duplicate records using fuzzy matching."""

    def find_duplicate_accounts(
        self, name: str, existing: List[Account], threshold: float = 0.8
    ) -> List[Account]:
        matches = []
        normalized = name.lower().strip()
        for account in existing:
            similarity = self._similarity(normalized, account.name.lower().strip())
            if similarity >= threshold:
                matches.append(account)
        return matches

    def _similarity(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        # Simple Jaccard similarity on character bigrams
        bigrams_a = set(a[i : i + 2] for i in range(len(a) - 1))
        bigrams_b = set(b[i : i + 2] for i in range(len(b) - 1))
        if not bigrams_a or not bigrams_b:
            return 0.0
        intersection = bigrams_a & bigrams_b
        union = bigrams_a | bigrams_b
        return len(intersection) / len(union)
