
"""
Add License Model

Revision ID: 1742713011
Revises: 1736687903
Create Date: 2025-03-23 06:56:51
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '1742713011'
down_revision = '1736687903'  # Reference the previous migration ID
branch_labels = None
depends_on = None

def upgrade():
    # Create 'license' table
    op.create_table(
        'licenses',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )

def downgrade():
    # Drop 'license' table
    op.drop_table('licenses')
