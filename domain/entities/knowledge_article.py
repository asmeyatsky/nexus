"""
Knowledge Article Entity

Architectural Intent:
- Knowledge base for support case resolution
- Article versioning and categorization
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from enum import Enum


class ArticleStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class KnowledgeArticle:
    id: str
    title: str
    body: str
    category: str
    status: ArticleStatus
    author_id: str
    org_id: str
    tags: tuple = ()
    view_count: int = 0
    helpful_count: int = 0
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        id: str,
        title: str,
        body: str,
        category: str,
        author_id: str,
        org_id: str,
        tags: tuple = (),
    ) -> "KnowledgeArticle":
        return KnowledgeArticle(
            id=id,
            title=title,
            body=body,
            category=category,
            status=ArticleStatus.DRAFT,
            author_id=author_id,
            org_id=org_id,
            tags=tags,
        )

    def publish(self) -> "KnowledgeArticle":
        return KnowledgeArticle(
            id=self.id,
            title=self.title,
            body=self.body,
            category=self.category,
            status=ArticleStatus.PUBLISHED,
            author_id=self.author_id,
            org_id=self.org_id,
            tags=self.tags,
            view_count=self.view_count,
            helpful_count=self.helpful_count,
            version=self.version,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )
