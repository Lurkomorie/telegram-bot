"""add cascade delete to persona history starts

Revision ID: 9f3e4c1a2b5d
Revises: 8dd047a735c0
Create Date: 2025-11-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f3e4c1a2b5d'
down_revision = '8dd047a735c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing foreign key constraint
    op.drop_constraint('persona_history_starts_persona_id_fkey', 'persona_history_starts', type_='foreignkey')
    
    # Re-add the foreign key constraint with CASCADE delete
    op.create_foreign_key(
        'persona_history_starts_persona_id_fkey',
        'persona_history_starts',
        'personas',
        ['persona_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop the CASCADE foreign key constraint
    op.drop_constraint('persona_history_starts_persona_id_fkey', 'persona_history_starts', type_='foreignkey')
    
    # Re-add the foreign key constraint without CASCADE
    op.create_foreign_key(
        'persona_history_starts_persona_id_fkey',
        'persona_history_starts',
        'personas',
        ['persona_id'],
        ['id']
    )

