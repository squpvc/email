"""
Migration to add tables for smart email management features.

This migration adds support for:
- Email categories and labels
- AI-powered actions and suggestions
- User behavior tracking for learning
- Outlook import tracking
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0002_add_smart_email_features'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # Create email_categories table
    op.create_table(
        'email_categories',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), nullable=False, default='#808080'),  # Default gray
        sa.Column('is_system', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Create email_labels table (sub-categories)
    op.create_table(
        'email_labels',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('email_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),  # Inherit from category if None
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('category_id', 'name', name='uq_category_label')
    )

    # Create email_actions table
    op.create_table(
        'email_actions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

    # Create email_category_mapping table
    op.create_table(
        'email_category_mapping',
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('email_categories.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('label_id', sa.Integer(), sa.ForeignKey('email_labels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),  # AI confidence score
        sa.Column('is_user_confirmed', sa.Boolean(), nullable=True),  # Null = not reviewed
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # Create email_actions_taken table
    op.create_table(
        'email_actions_taken',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('email_id', sa.Integer(), sa.ForeignKey('emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_id', sa.Integer(), sa.ForeignKey('email_actions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),  # Store action-specific parameters
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Index('idx_email_actions_taken_email', 'email_id'),
        sa.Index('idx_email_actions_taken_user', 'user_id')
    )

    # Create user_behavior table for learning
    op.create_table(
        'user_behavior',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('behavior_type', sa.String(50), nullable=False),  # 'category', 'action', 'label', etc.
        sa.Column('pattern', sa.JSON(), nullable=False),  # JSON pattern that triggered the behavior
        sa.Column('action', sa.String(100), nullable=False),  # The action taken
        sa.Column('action_parameters', sa.JSON(), nullable=True),  # Parameters for the action
        sa.Column('count', sa.Integer(), nullable=False, default=1),
        sa.Column('last_used', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Index('idx_user_behavior_type', 'behavior_type'),
        sa.Index('idx_user_behavior_user', 'user_id')
    )

    # Create outlook_imports table
    op.create_table(
        'outlook_imports',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('imported_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),  # pending, in_progress, completed, failed
        sa.Column('stats', sa.JSON(), nullable=True),  # Store import statistics
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True)
    )

    # Create outlook_import_mapping table
    op.create_table(
        'outlook_import_mapping',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('import_id', sa.Integer(), sa.ForeignKey('outlook_imports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlook_folder', sa.String(500), nullable=False),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('email_categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('label_id', sa.Integer(), sa.ForeignKey('email_labels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('item_count', sa.Integer(), nullable=False, default=0),
        sa.Index('idx_outlook_import_mapping_import', 'import_id')
    )

def downgrade():
    # Drop tables in reverse order
    op.drop_table('outlook_import_mapping')
    op.drop_table('outlook_imports')
    op.drop_table('user_behavior')
    op.drop_table('email_actions_taken')
    op.drop_table('email_category_mapping')
    op.drop_table('email_actions')
    op.drop_table('email_labels')
    op.drop_table('email_categories')
