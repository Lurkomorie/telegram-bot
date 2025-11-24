"""Add token system, premium tiers, referrals, and payment transactions

Revision ID: 022
Revises: d97e2ee04e72
Create Date: 2025-01-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '022'
down_revision = 'd97e2ee04e72'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to users table
    op.add_column('users', 
                  sa.Column('premium_tier', sa.String(20), nullable=False, server_default='free'))
    op.add_column('users',
                  sa.Column('last_daily_token_addition', sa.DateTime(), nullable=True))
    op.add_column('users',
                  sa.Column('last_daily_bonus_claim', sa.DateTime(), nullable=True))
    op.add_column('users',
                  sa.Column('referred_by_user_id', sa.BigInteger(), nullable=True))
    op.add_column('users',
                  sa.Column('referral_tokens_awarded', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add foreign key for referred_by_user_id
    op.create_foreign_key(
        'fk_users_referred_by_user_id',
        'users',
        'users',
        ['referred_by_user_id'],
        ['id']
    )
    
    # Create indexes for new columns
    op.create_index('ix_users_premium_tier', 'users', ['premium_tier'])
    op.create_index('ix_users_referred_by_user_id', 'users', ['referred_by_user_id'])
    
    # Migrate existing premium users to "premium" tier
    op.execute("""
        UPDATE users
        SET premium_tier = 'premium'
        WHERE is_premium = true AND (premium_until IS NULL OR premium_until > NOW())
    """)
    
    # Drop max_energy column (no longer needed)
    op.drop_column('users', 'max_energy')
    
    # Create payment_transactions table
    op.create_table(
        'payment_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('transaction_type', sa.String(20), nullable=False),
        sa.Column('product_id', sa.String(50), nullable=False),
        sa.Column('amount_stars', sa.BigInteger(), nullable=False),
        sa.Column('tokens_received', sa.BigInteger(), nullable=True),
        sa.Column('tier_granted', sa.String(20), nullable=True),
        sa.Column('subscription_days', sa.BigInteger(), nullable=True),
        sa.Column('telegram_payment_charge_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='completed'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("transaction_type IN ('token_package', 'tier_subscription')", name='check_transaction_type'),
        sa.CheckConstraint("status IN ('completed', 'pending', 'failed', 'refunded')", name='check_status'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for payment_transactions
    op.create_index('ix_payment_transactions_user_id', 'payment_transactions', ['user_id'])
    op.create_index('ix_payment_transactions_created_at', 'payment_transactions', ['created_at'])
    op.create_index('ix_payment_transactions_status', 'payment_transactions', ['status'])


def downgrade():
    # Drop payment_transactions table
    op.drop_index('ix_payment_transactions_status', table_name='payment_transactions')
    op.drop_index('ix_payment_transactions_created_at', table_name='payment_transactions')
    op.drop_index('ix_payment_transactions_user_id', table_name='payment_transactions')
    op.drop_table('payment_transactions')
    
    # Re-add max_energy column
    op.add_column('users', sa.Column('max_energy', sa.BigInteger(), nullable=False, server_default='100'))
    
    # Drop indexes for users
    op.drop_index('ix_users_referred_by_user_id', table_name='users')
    op.drop_index('ix_users_premium_tier', table_name='users')
    
    # Drop foreign key
    op.drop_constraint('fk_users_referred_by_user_id', 'users', type_='foreignkey')
    
    # Drop new columns from users
    op.drop_column('users', 'referral_tokens_awarded')
    op.drop_column('users', 'referred_by_user_id')
    op.drop_column('users', 'last_daily_bonus_claim')
    op.drop_column('users', 'last_daily_token_addition')
    op.drop_column('users', 'premium_tier')

