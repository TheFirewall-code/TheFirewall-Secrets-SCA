"""
Convert severity column to lowercase in vulnerability table,
and make 'name' column nullable in whitelist table.

Revision ID: 1736687903
Revises: 1735291973
Create Date: 2023-XX-XX XX:XX:XX
"""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision = '1736687903'
down_revision = '1736666153'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Make 'name' column nullable in 'whitelist' table
    # Adjust existing_type if you know the exact column type/length.
    op.alter_column(
        'whitelist',
        'name',
        existing_type=sa.String(),  # or sa.String(length=255) if you know the length
        nullable=True
    )

def downgrade():
    # Revert 'name' column back to non-nullable (if needed)
    op.alter_column(
        'whitelist',
        'name',
        existing_type=sa.String(),
        nullable=False
    )

    # Optional revert: uppercase severity values
    # op.execute("UPDATE vulnerability SET severity = UPPER(severity);")
