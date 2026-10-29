"""availability declared by referee

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('availability') as batch:
        batch.add_column(sa.Column('declared_by_referee', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('declared_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('availability') as batch:
        batch.drop_column('declared_at')
        batch.drop_column('declared_by_referee')
