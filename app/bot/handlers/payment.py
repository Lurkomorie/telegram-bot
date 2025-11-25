"""
Payment handlers for Telegram Stars
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router
from app.db.base import get_db
from app.db import crud

# Payment products: token packages and tier subscriptions
PAYMENT_PRODUCTS = {
    # Token packages (one-time purchases) - exact pricing from screenshot
    "tokens_50": {"type": "tokens", "amount": 50, "stars": 35},
    "tokens_100": {"type": "tokens", "amount": 100, "stars": 70},
    "tokens_250": {"type": "tokens", "amount": 250, "stars": 175},
    "tokens_500": {"type": "tokens", "amount": 500, "stars": 350},
    "tokens_1000": {"type": "tokens", "amount": 1000, "stars": 700},
    "tokens_2500": {"type": "tokens", "amount": 2500, "stars": 1750},
    "tokens_5000": {"type": "tokens", "amount": 5000, "stars": 3500},
    "tokens_10000": {"type": "tokens", "amount": 10000, "stars": 7000},
    "tokens_25000": {"type": "tokens", "amount": 25000, "stars": 17500},
    
    # Tier subscriptions (30 days)
    "plus_month": {"type": "tier", "tier": "plus", "duration": 30, "stars": 325, "daily_tokens": 25},
    "pro_month": {"type": "tier", "tier": "pro", "duration": 30, "stars": 625, "daily_tokens": 75},
    "legendary_month": {"type": "tier", "tier": "legendary", "duration": 30, "stars": 775, "daily_tokens": 100},
    
    # Tier subscriptions (90 days) - 5% discount
    "plus_3months": {"type": "tier", "tier": "plus", "duration": 90, "stars": 926, "daily_tokens": 25},
    "pro_3months": {"type": "tier", "tier": "pro", "duration": 90, "stars": 1781, "daily_tokens": 75},
    "legendary_3months": {"type": "tier", "tier": "legendary", "duration": 90, "stars": 2209, "daily_tokens": 100},
    
    # Tier subscriptions (180 days) - 10% discount
    "plus_6months": {"type": "tier", "tier": "plus", "duration": 180, "stars": 1755, "daily_tokens": 25},
    "pro_6months": {"type": "tier", "tier": "pro", "duration": 180, "stars": 3375, "daily_tokens": 75},
    "legendary_6months": {"type": "tier", "tier": "legendary", "duration": 180, "stars": 4185, "daily_tokens": 100},
}


@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: types.PreCheckoutQuery):
    """
    Handle pre-checkout query - validate payment before processing
    This is called by Telegram before charging the user
    """
    # Always approve - we validate on successful payment
    await pre_checkout_query.answer(ok=True)


@router.message(lambda message: message.successful_payment)
async def successful_payment_handler(message: types.Message):
    """
    Handle successful payment - process token package or tier subscription
    """
    payment = message.successful_payment
    user_id = message.from_user.id
    
    # Extract product_id from invoice payload
    product_id = payment.invoice_payload
    
    print(f"[PAYMENT] ✅ Successful payment from user {user_id}, product: {product_id}")
    print(f"[PAYMENT] Amount: {payment.total_amount} {payment.currency}")
    
    # Get product details
    if product_id not in PAYMENT_PRODUCTS:
        await message.answer("❌ Invalid product. Please contact support.")
        return
    
    product = PAYMENT_PRODUCTS[product_id]
    product_type = product["type"]
    
    with get_db() as db:
        if product_type == "tokens":
            # Token package purchase
            tokens_amount = product["amount"]
            success = crud.add_user_energy(db, user_id, tokens_amount)
            
            if success:
                # Create transaction record
                crud.create_payment_transaction(
                    db=db,
                    user_id=user_id,
                    transaction_type="token_package",
                    product_id=product_id,
                    amount_stars=product["stars"],
                    tokens_received=tokens_amount,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id
                )
                
                # Get updated balance
                user = crud.get_or_create_user(db, user_id)
                
                await message.answer(
                    f"🪙 <b>Tokens Purchased!</b>\n\n"
                    f"✨ +{tokens_amount} tokens added to your account!\n"
                    f"💰 Current balance: <b>{user.energy} tokens</b>\n\n"
                    f"Thank you for your purchase! 💎"
                )
                
                print(f"[PAYMENT] ✅ Added {tokens_amount} tokens to user {user_id}")
            else:
                await message.answer("❌ Failed to add tokens. Please contact support.")
                print(f"[PAYMENT] ❌ Failed to add tokens for user {user_id}")
        
        elif product_type == "tier":
            # Tier subscription purchase
            tier = product["tier"]
            duration_days = product["duration"]
            daily_tokens = product["daily_tokens"]
            
            success = crud.activate_premium(db, user_id, duration_days, tier)
            
            if success:
                # Create transaction record
                crud.create_payment_transaction(
                    db=db,
                    user_id=user_id,
                    transaction_type="tier_subscription",
                    product_id=product_id,
                    amount_stars=product["stars"],
                    tier_granted=tier,
                    subscription_days=duration_days,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id
                )
                
                # Get updated user info
                user = crud.get_or_create_user(db, user_id)
                premium_until = user.premium_until.strftime("%Y-%m-%d") if user.premium_until else "Forever"
                
                tier_names = {
                    "plus": "Plus",
                    "premium": "Premium",
                    "pro": "Pro",
                    "legendary": "Legendary"
                }
                tier_display = tier_names.get(tier, tier.capitalize())
                
                await message.answer(
                    f"🎉 <b>Welcome to {tier_display}!</b>\n\n"
                    f"✨ Your {tier_display} subscription is now active!\n"
                    f"📅 Valid until: <b>{premium_until}</b>\n\n"
                    f"Benefits:\n"
                    f"🪙 +{daily_tokens} tokens every day\n"
                    f"🎁 Daily bonus rewards\n"
                    f"🚀 Enjoy the full experience!\n\n"
                    f"Thank you for your support! 💎"
                )
                
                print(f"[PAYMENT] ✅ Activated {tier} tier for user {user_id} for {duration_days} days")
            else:
                await message.answer("❌ Failed to activate subscription. Please contact support.")
                print(f"[PAYMENT] ❌ Failed to activate {tier} tier for user {user_id}")


@router.message(Command("premium_status"))
async def cmd_premium_status(message: types.Message):
    """Check premium subscription status"""
    user_id = message.from_user.id
    
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)["is_premium"]
        user = crud.get_or_create_user(db, user_id)
        
        if is_premium:
            premium_until = user.premium_until.strftime("%Y-%m-%d %H:%M UTC") if user.premium_until else "Forever"
            await message.answer(
                f"💎 <b>Premium Status</b>\n\n"
                f"✨ You have an active premium subscription!\n"
                f"📅 Valid until: <b>{premium_until}</b>\n\n"
                f"Benefits:\n"
                f"⚡ Unlimited energy\n"
                f"📸 Free image generation"
            )
        else:
            energy_info = crud.get_user_energy(db, user_id)
            await message.answer(
                f"🆓 <b>Free Account</b>\n\n"
                f"⚡ Energy: {energy_info['energy']}/{energy_info['max_energy']}\n"
                f"🔄 You receive +10 energy daily\n\n"
                f"💎 Upgrade to Premium for unlimited energy!\n"
                f"Use /start to access the premium plans."
            )

