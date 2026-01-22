"""reduce max energy to 80

Revision ID: 029_reduce_max_energy_to_80
Revises: e021a6635b20
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '029_reduce_max_energy_to_80'
down_revision = 'e021a6635b20'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update default values for new users
    op.alter_column('users', 'energy',
                    existing_type=sa.BigInteger(),
                    server_default='80',
                    existing_nullable=False)
    
    op.alter_column('users', 'max_energy',
                    existing_type=sa.BigInteger(),
                    server_default='80',
                    existing_nullable=False)
    
    # Update existing users who have 100 energy to 80
    # Only update users who have exactly 100 (default value)
    op.execute("""
        UPDATE users 
        SET energy = 80, max_energy = 80 
        WHERE energy = 100 AND max_energy = 100
    """)


def downgrade() -> None:
    # Revert to 100
    op.alter_column('users', 'energy',
                    existing_type=sa.BigInteger(),
                    server_default='100',
                    existing_nullable=False)
    
    op.alter_column('users', 'max_energy',
                    existing_type=sa.BigInteger(),
                    server_default='100',
                    existing_nullable=False)
    
    # Revert existing users
    op.execute("""
        UPDATE users 
        SET energy = 100, max_energy = 100 
        WHERE energy = 80 AND max_energy = 80
    """)
