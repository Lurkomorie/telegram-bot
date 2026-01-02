"""Add style to personas (stub migration - original was removed)

Revision ID: add_style_to_personas
Revises: 028
Create Date: 2025-12-20

This is a stub migration. The original migration file was deleted,
but the TEST database still references this revision. This stub
allows Alembic to continue working.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_style_to_personas'
down_revision: Union[str, None] = '028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Stub - no changes needed
    pass


def downgrade() -> None:
    # Stub - no changes needed
    pass

