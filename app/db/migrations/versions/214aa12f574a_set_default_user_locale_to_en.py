"""set_default_user_locale_to_en

Revision ID: 214aa12f574a
Revises: 021
Create Date: 2025-11-15 21:50:51.548644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '214aa12f574a'
down_revision: Union[str, None] = '021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Set default locale to 'en' for all existing users where locale is NULL or empty
    op.execute("""
        UPDATE users 
        SET locale = 'en' 
        WHERE locale IS NULL OR locale = ''
    """)


def downgrade() -> None:
    # No downgrade needed - we don't want to remove language preferences
    pass


