"""publications

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('publications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_from', sa.Date(), nullable=False),
    sa.Column('date_to', sa.Date(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('published_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    sa.Column('rows', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_publications'))
    )
    op.create_index(op.f('ix_publications_date_from'), 'publications', ['date_from'], unique=False)
    op.create_index(op.f('ix_publications_date_to'), 'publications', ['date_to'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_publications_date_to'), table_name='publications')
    op.drop_index(op.f('ix_publications_date_from'), table_name='publications')
    op.drop_table('publications')
