"""
Tests for InMemoryCaseRepository.
"""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from uuid import uuid4

from domain.entities.case import Case, CaseStatus
from infrastructure.mcp_servers.nexus_crm_server import InMemoryCaseRepository


def make_case(account_id=None, case_number="CASE-001") -> Case:
    return Case.create(
        subject="Test Issue",
        description="Something is broken",
        account_id=account_id or uuid4(),
        owner_id=uuid4(),
        case_number=case_number,
    )


@pytest.mark.asyncio
async def test_case_repo_save_and_get_by_id():
    repo = InMemoryCaseRepository()
    case = make_case()
    await repo.save(case)

    found = await repo.get_by_id(case.id)
    assert found is not None
    assert str(found.id) == str(case.id)
    assert found.subject == "Test Issue"


@pytest.mark.asyncio
async def test_case_repo_get_open_cases():
    repo = InMemoryCaseRepository()
    account_id = uuid4()

    open_case1 = make_case(account_id=account_id, case_number="CASE-001")
    open_case2 = make_case(account_id=account_id, case_number="CASE-002")
    resolved_case = (
        make_case(account_id=account_id, case_number="CASE-003")
        .change_status(CaseStatus.IN_PROGRESS)
        .resolve("Fixed", "agent@company.com")
    )
    closed_case = (
        make_case(account_id=account_id, case_number="CASE-004")
        .change_status(CaseStatus.IN_PROGRESS)
        .resolve("Fixed too", "agent@company.com")
        .close()
    )

    await repo.save(open_case1)
    await repo.save(open_case2)
    await repo.save(resolved_case)
    await repo.save(closed_case)

    open_cases = await repo.get_open_cases()
    assert len(open_cases) == 2
    open_ids = {str(c.id) for c in open_cases}
    assert str(open_case1.id) in open_ids
    assert str(open_case2.id) in open_ids


@pytest.mark.asyncio
async def test_case_repo_get_all_with_pagination():
    repo = InMemoryCaseRepository()
    account_id = uuid4()

    for i in range(5):
        await repo.save(make_case(account_id=account_id, case_number=f"CASE-{i:03d}"))

    all_cases = await repo.get_all(limit=100, offset=0)
    assert len(all_cases) == 5

    page1 = await repo.get_all(limit=2, offset=0)
    assert len(page1) == 2

    page2 = await repo.get_all(limit=2, offset=2)
    assert len(page2) == 2

    page3 = await repo.get_all(limit=10, offset=4)
    assert len(page3) == 1


@pytest.mark.asyncio
async def test_case_repo_delete():
    repo = InMemoryCaseRepository()
    case = make_case()
    await repo.save(case)

    await repo.delete(case.id)

    found = await repo.get_by_id(case.id)
    assert found is None
