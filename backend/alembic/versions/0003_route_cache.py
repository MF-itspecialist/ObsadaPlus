"""route cache

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'route_cache',
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('origin_lat', sa.Float(), nullable=False),
        sa.Column('origin_lon', sa.Float(), nullable=False),
        sa.Column('dest_lat', sa.Float(), nullable=False),
        sa.Column('dest_lon', sa.Float(), nullable=False),
        sa.Column('distance_km', sa.Float(), nullable=False),
        sa.Column('travel_minutes', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('provider', 'origin_lat', 'origin_lon', 'dest_lat', 'dest_lon', name=op.f('pk_route_cache')),
    )


def downgrade() -> None:
    op.drop_table('route_cache')
