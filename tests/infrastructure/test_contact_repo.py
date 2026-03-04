"""
Tests for InMemoryContactRepository.
"""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from uuid import uuid4

from domain.entities.contact import Contact
from domain.value_objects import Email
from infrastructure.mcp_servers.nexus_crm_server import InMemoryContactRepository


def make_contact(account_id=None, email_suffix="test") -> Contact:
    return Contact.create(
        account_id=account_id or uuid4(),
        first_name="Alice",
        last_name="Smith",
        email=Email.create(f"alice.{email_suffix}@example.com"),
        owner_id=uuid4(),
    )


@pytest.mark.asyncio
async def test_contact_repo_save_and_get_by_id():
    repo = InMemoryContactRepository()
    contact = make_contact()
    await repo.save(contact)

    found = await repo.get_by_id(contact.id)
    assert found is not None
    assert str(found.id) == str(contact.id)
    assert found.first_name == "Alice"


@pytest.mark.asyncio
async def test_contact_repo_get_by_account():
    repo = InMemoryContactRepository()
    account_id_a = uuid4()
    account_id_b = uuid4()

    for i in range(3):
        await repo.save(make_contact(account_id=account_id_a, email_suffix=f"a{i}"))
    await repo.save(make_contact(account_id=account_id_b, email_suffix="b0"))

    contacts_a = await repo.get_by_account(account_id_a)
    assert len(contacts_a) == 3
    for c in contacts_a:
        assert str(c.account_id) == str(account_id_a)

    contacts_b = await repo.get_by_account(account_id_b)
    assert len(contacts_b) == 1


@pytest.mark.asyncio
async def test_contact_repo_get_all_with_pagination():
    repo = InMemoryContactRepository()
    account_id = uuid4()

    for i in range(5):
        await repo.save(make_contact(account_id=account_id, email_suffix=str(i)))

    all_contacts = await repo.get_all(limit=100, offset=0)
    assert len(all_contacts) == 5

    page1 = await repo.get_all(limit=2, offset=0)
    assert len(page1) == 2

    page2 = await repo.get_all(limit=2, offset=2)
    assert len(page2) == 2

    page3 = await repo.get_all(limit=2, offset=4)
    assert len(page3) == 1


@pytest.mark.asyncio
async def test_contact_repo_delete():
    repo = InMemoryContactRepository()
    contact = make_contact()
    await repo.save(contact)

    await repo.delete(contact.id)

    found = await repo.get_by_id(contact.id)
    assert found is None
