"""Add practice_sessions table and session_id to practice_attempts.

Revision ID: 9a1b2c3d4e5f
Revises: 7808c36c4035
Create Date: 2026-11-03 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1b2c3d4e5f'
down_revision: Union[str, None] = '7808c36c4035'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'practice_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('difficulty', sa.String(length=20), nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('question_ids', sa.JSON(), nullable=False),
        sa.Column('current_index', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('time_limit_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_practice_sessions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_practice_sessions'))
    )
    with op.batch_alter_table('practice_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_practice_sessions_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_practice_sessions_session_id'), ['session_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_practice_sessions_user_id'), ['user_id'], unique=False)

    with op.batch_alter_table('practice_attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f('ix_practice_attempts_session_id'), ['session_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('practice_attempts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_practice_attempts_session_id'))
        batch_op.drop_column('session_id')

    with op.batch_alter_table('practice_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_practice_sessions_user_id'))
        batch_op.drop_index(batch_op.f('ix_practice_sessions_session_id'))
        batch_op.drop_index(batch_op.f('ix_practice_sessions_id'))

    op.drop_table('practice_sessions')

