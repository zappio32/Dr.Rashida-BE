"""baseline (no-op, matches existing prisma-managed schema)

Revision ID: 30ebae28b1e7
Revises: 
Create Date: 2026-08-20 19:09:18.345289

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30ebae28b1e7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
