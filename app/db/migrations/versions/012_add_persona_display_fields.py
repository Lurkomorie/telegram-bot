"""Add display fields to personas and persona history starts

Revision ID: 012
Revises: 011
Create Date: 2025-10-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    # Add display fields to personas table
    op.add_column('personas', 
                  sa.Column('small_description', sa.Text(), nullable=True))
    op.add_column('personas',
                  sa.Column('emoji', sa.String(10), nullable=True))
    
    # Add display fields to persona_history_starts table
    op.add_column('persona_history_starts',
                  sa.Column('name', sa.String(255), nullable=True))
    op.add_column('persona_history_starts',
                  sa.Column('small_description', sa.Text(), nullable=True))


def downgrade():
    # Remove display fields from persona_history_starts
    op.drop_column('persona_history_starts', 'small_description')
    op.drop_column('persona_history_starts', 'name')
    
    # Remove display fields from personas
    op.drop_column('personas', 'emoji')
    op.drop_column('personas', 'small_description')

