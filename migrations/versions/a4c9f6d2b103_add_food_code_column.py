"""add indexed food_code column and backfill from metadata

Revision ID: a4c9f6d2b103
Revises: 3f07bda3c5dc
Create Date: 2026-11-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4c9f6d2b103"
down_revision: Union[str, Sequence[str], None] = "3f07bda3c5dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("food_code", sa.String(length=64), nullable=True))
    op.execute(
        sa.text("UPDATE documents SET food_code = metadata ->> 'food_code'")
    )
    op.create_index("ix_documents_food_code", "documents", ["food_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_food_code", table_name="documents")
    op.drop_column("documents", "food_code")
