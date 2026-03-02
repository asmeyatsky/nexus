"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-02

Creates all core tables: accounts, contacts, opportunities, leads, cases, users.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(100), nullable=False),
        sa.Column("territory", sa.String(100), nullable=False),
        sa.Column("website", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("billing_address", sa.Text),
        sa.Column("annual_revenue", sa.Numeric(15, 2)),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("employee_count", sa.Integer),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "parent_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id"),
        ),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("title", sa.String(100)),
        sa.Column("department", sa.String(100)),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("probability", sa.Integer, server_default="10"),
        sa.Column("close_date", sa.DateTime, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id"),
        ),
        sa.Column("source", sa.String(50)),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("closed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="new"),
        sa.Column("rating", sa.String(50), server_default="cold"),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(50)),
        sa.Column("phone", sa.String(50)),
        sa.Column("title", sa.String(100)),
        sa.Column("website", sa.String(255)),
        sa.Column(
            "converted_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id"),
        ),
        sa.Column(
            "converted_contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id"),
        ),
        sa.Column(
            "converted_opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id"),
        ),
        sa.Column("converted_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("case_number", sa.String(50), unique=True, nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id"),
        ),
        sa.Column("status", sa.String(50), server_default="new"),
        sa.Column("priority", sa.String(50), server_default="medium"),
        sa.Column("origin", sa.String(50), server_default="web"),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resolution_notes", sa.Text),
        sa.Column("resolved_by", sa.String(100)),
        sa.Column("resolved_at", sa.DateTime),
        sa.Column("closed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("password_history", sa.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("cases")
    op.drop_table("leads")
    op.drop_table("opportunities")
    op.drop_table("contacts")
    op.drop_table("accounts")
