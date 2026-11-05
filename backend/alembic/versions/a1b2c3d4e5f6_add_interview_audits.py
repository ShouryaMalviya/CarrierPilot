"""Add interview_audits table for evaluation quality and safety tracking.

Revision ID: a1b2c3d4e5f6
Revises: 9a1b2c3d4e5f
Create Date: 2026-11-05 19:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'interview_audits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rubric_version', sa.String(length=50), nullable=False),
        sa.Column('model_provider', sa.String(length=50), nullable=False),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('fallback_reason', sa.Text(), nullable=True),
        sa.Column('prompt_injection_detected', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('raw_score', sa.Float(), nullable=False),
        sa.Column('bounded_score', sa.Float(), nullable=False),
        sa.Column('dimension_scores_snapshot', sa.JSON(), nullable=True),
        sa.Column('response_word_count', sa.Integer(), nullable=False),
        sa.Column('response_char_count', sa.Integer(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], name=op.f('fk_interview_audits_session_id_interview_sessions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_interview_audits_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_interview_audits'))
    )
    with op.batch_alter_table('interview_audits', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_interview_audits_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_interview_audits_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_interview_audits_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('interview_audits', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_interview_audits_user_id'))
        batch_op.drop_index(batch_op.f('ix_interview_audits_session_id'))
        batch_op.drop_index(batch_op.f('ix_interview_audits_id'))

    op.drop_table('interview_audits')

