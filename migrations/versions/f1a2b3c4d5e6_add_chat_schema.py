"""Add chat schema (threads, messages, artifacts, checkpoints).

Revision ID: f1a2b3c4d5e6
Revises: dddd991f35d7
Create Date: 2024-04-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'dddd991f35d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create chat schema tables."""
    # Create chat_threads table
    op.create_table(
        'chat_threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id'),
    )
    op.create_index('ix_chat_threads_thread_id', 'chat_threads', ['thread_id'])
    op.create_index('ix_chat_threads_user_id', 'chat_threads', ['user_id'])

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.String(255), nullable=False),
        sa.Column('sender_role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id'),
    )
    op.create_index('ix_chat_messages_thread_id', 'chat_messages', ['thread_id'])
    op.create_index('ix_chat_messages_message_id', 'chat_messages', ['message_id'])

    # Create chat_artifacts table
    op.create_table(
        'chat_artifacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artifact_id', sa.String(255), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('compressed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('data', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artifact_id'),
    )
    op.create_index('ix_chat_artifacts_artifact_id', 'chat_artifacts', ['artifact_id'])
    op.create_index('ix_chat_artifacts_thread_id', 'chat_artifacts', ['thread_id'])

    # Create chat_checkpoints table
    op.create_table(
        'chat_checkpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('checkpoint_id', sa.String(255), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.String(255), nullable=False),
        sa.Column('checkpoint_index', sa.Integer(), nullable=False),
        sa.Column('graph_state_json', postgresql.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('checkpoint_id'),
    )
    op.create_index('ix_chat_checkpoints_checkpoint_id', 'chat_checkpoints', ['checkpoint_id'])
    op.create_index('ix_chat_checkpoints_thread_id', 'chat_checkpoints', ['thread_id'])


def downgrade() -> None:
    """Drop chat schema tables."""
    op.drop_index('ix_chat_checkpoints_thread_id', table_name='chat_checkpoints')
    op.drop_index('ix_chat_checkpoints_checkpoint_id', table_name='chat_checkpoints')
    op.drop_table('chat_checkpoints')

    op.drop_index('ix_chat_artifacts_thread_id', table_name='chat_artifacts')
    op.drop_index('ix_chat_artifacts_artifact_id', table_name='chat_artifacts')
    op.drop_table('chat_artifacts')

    op.drop_index('ix_chat_messages_message_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_thread_id', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('ix_chat_threads_user_id', table_name='chat_threads')
    op.drop_index('ix_chat_threads_thread_id', table_name='chat_threads')
    op.drop_table('chat_threads')
