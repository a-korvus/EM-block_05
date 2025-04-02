"""first_migration.

Revision ID: 149b4cdf59cf
Revises:
Create Date: 2025-03-21 11:26:18.731675
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "149b4cdf59cf"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "spimex_trading_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_product_id", sa.String(length=11), nullable=False),
        sa.Column(
            "exchange_product_name", sa.String(length=255), nullable=False
        ),
        sa.Column("oil_id", sa.String(length=4), nullable=False),
        sa.Column("delivery_basis_id", sa.String(length=3), nullable=False),
        sa.Column(
            "delivery_basis_name", sa.String(length=255), nullable=False
        ),
        sa.Column("delivery_type_id", sa.String(length=1), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column(
            "created_on",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_on",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("spimex_trading_results")
