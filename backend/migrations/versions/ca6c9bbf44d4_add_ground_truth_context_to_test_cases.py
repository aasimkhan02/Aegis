"""add ground_truth_context to test_cases

Revision ID: ca6c9bbf44d4
Revises: b80bdc4f2907
Create Date: 2026-11-05 19:39:32.115140
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'ca6c9bbf44d4'
down_revision: Union[str, None] = 'b80bdc4f2907'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'test_cases',
        sa.Column(
            'ground_truth_context',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('test_cases', 'ground_truth_context')

