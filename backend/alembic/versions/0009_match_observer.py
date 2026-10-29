"""match observer flag

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.add_column(sa.Column('observer_required', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('observer_manual', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.drop_column('observer_manual')
        batch.drop_column('observer_required')
