"""import runs (automatic match updates)

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'import_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source', sa.String(length=40), nullable=False),
        sa.Column('trigger', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created', sa.Integer(), nullable=False),
        sa.Column('updated', sa.Integer(), nullable=False),
        sa.Column('changes', sa.JSON(), nullable=False),
        sa.Column('messages', sa.JSON(), nullable=False),
    )
    op.create_index('ix_import_runs_started_at', 'import_runs', ['started_at'])


def downgrade() -> None:
    op.drop_index('ix_import_runs_started_at', table_name='import_runs')
    op.drop_table('import_runs')
