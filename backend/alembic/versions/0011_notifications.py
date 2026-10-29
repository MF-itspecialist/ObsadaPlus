"""e-mail notifications: referee contact, outbox

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('referees') as batch:
        batch.add_column(sa.Column('email', sa.String(length=200), nullable=False, server_default=''))
        batch.add_column(sa.Column('notify_email', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table(
        'outbox_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('referee_id', sa.Integer(), sa.ForeignKey('referees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('to_email', sa.String(length=200), nullable=False),
        sa.Column('to_name', sa.String(length=200), nullable=False),
        sa.Column('kind', sa.String(length=30), nullable=False),
        sa.Column('topic', sa.String(length=60), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error', sa.String(length=500), nullable=False),
    )
    op.create_index('ix_outbox_messages_created_at', 'outbox_messages', ['created_at'])
    op.create_index('ix_outbox_messages_topic', 'outbox_messages', ['topic'])


def downgrade() -> None:
    op.drop_index('ix_outbox_messages_topic', table_name='outbox_messages')
    op.drop_index('ix_outbox_messages_created_at', table_name='outbox_messages')
    op.drop_table('outbox_messages')
    with op.batch_alter_table('referees') as batch:
        batch.drop_column('notify_email')
        batch.drop_column('email')
