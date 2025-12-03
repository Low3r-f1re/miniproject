"""Add user location fields for budget calculations

Revision ID: 001_add_location
Revises: 
Create Date: 2025-11-30 23:29:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_location'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add location fields to users table
    op.add_column('users', sa.Column('home_city', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('home_country', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('home_latitude', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('home_longitude', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('currency_code', sa.String(length=3), nullable=True, server_default='USD'))


def downgrade():
    # Remove location fields from users table
    op.drop_column('users', 'currency_code')
    op.drop_column('users', 'home_longitude')
    op.drop_column('users', 'home_latitude')
    op.drop_column('users', 'home_country')
    op.drop_column('users', 'home_city')
