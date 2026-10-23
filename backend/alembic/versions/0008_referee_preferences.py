"""referee preferences: leagues, clubs, region

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('referees') as batch:
        batch.add_column(sa.Column('preferred_leagues', sa.JSON(), nullable=False, server_default='[]'))
        batch.add_column(sa.Column('avoided_clubs', sa.JSON(), nullable=False, server_default='[]'))
        batch.add_column(sa.Column('conflict_clubs', sa.JSON(), nullable=False, server_default='[]'))
        batch.add_column(sa.Column('own_region_only', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('referees') as batch:
        batch.drop_column('own_region_only')
        batch.drop_column('conflict_clubs')
        batch.drop_column('avoided_clubs')
        batch.drop_column('preferred_leagues')
