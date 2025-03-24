"""
Convert severity column to lowercase

Revision ID: 1736666153
Revises: 1735291973
Create Date: 2023-XX-XX XX:XX:XX
"""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision = '1736666153'
down_revision = '1735291973'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Convert existing severity values to lowercase
    op.execute("UPDATE vulnerability SET severity = LOWER(severity);")

def downgrade():
    # Optional: If you need to revert, you could uppercase them or leave as a no-op.
    # op.execute("UPDATE vulnerability SET severity = UPPER(severity);")
    pass
