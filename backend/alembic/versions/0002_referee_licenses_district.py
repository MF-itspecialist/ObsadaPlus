"""referee licenses and district

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('referees', sa.Column('district', sa.String(length=100), nullable=False, server_default=''))
    op.add_column('referees', sa.Column('licenses', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    op.drop_column('referees', 'licenses')
    op.drop_column('referees', 'district')
