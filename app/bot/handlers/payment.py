"""
Payment handlers for Telegram Stars
"""
from aiogram import types
from aiogram.filters import Command
from app.bot.loader import router
from app.db.base import get_db
from app.db import crud

# Plan mapping: plan_id -> (duration_days, stars_price)
PREMIUM_PLANS = {
    "2days": (2, 250),
    "month": (30, 500),
    "3months": (90, 1000),
    "year": (365, 3000),
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
    Handle successful payment - activate premium subscription
    """
    payment = message.successful_payment
    user_id = message.from_user.id
    
    # Extract plan_id from invoice payload
    plan_id = payment.invoice_payload
    
    print(f"[PAYMENT] ✅ Successful payment from user {user_id}, plan: {plan_id}")
    print(f"[PAYMENT] Amount: {payment.total_amount} {payment.currency}")
    
    # Get plan details
    if plan_id not in PREMIUM_PLANS:
        await message.answer("❌ Invalid plan. Please contact support.")
        return
    
    duration_days, _stars_price = PREMIUM_PLANS[plan_id]
    
    # Activate premium subscription
    with get_db() as db:
        success = crud.activate_premium(db, user_id, duration_days)
        
        if success:
            # Get updated user info
            user = crud.get_or_create_user(db, user_id)
            premium_until = user.premium_until.strftime("%Y-%m-%d") if user.premium_until else "Forever"
            
            await message.answer(
                f"🎉 <b>Welcome to Premium!</b>\n\n"
                f"✨ Your premium subscription is now active!\n"
                f"📅 Valid until: <b>{premium_until}</b>\n\n"
                f"Premium benefits:\n"
                f"⚡ Unlimited energy - free image generation\n"
                f"📸 Generate as many images as you want\n"
                f"🚀 Enjoy the full experience!\n\n"
                f"Thank you for your support! 💎"
            )
            
            print(f"[PAYMENT] ✅ Activated premium for user {user_id} for {duration_days} days")
        else:
            await message.answer("❌ Failed to activate premium. Please contact support.")
            print(f"[PAYMENT] ❌ Failed to activate premium for user {user_id}")


@router.message(Command("premium_status"))
async def cmd_premium_status(message: types.Message):
    """Check premium subscription status"""
    user_id = message.from_user.id
    
    with get_db() as db:
        is_premium = crud.check_user_premium(db, user_id)
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
                f"🔄 You receive +20 energy daily\n\n"
                f"💎 Upgrade to Premium for unlimited energy!\n"
                f"Use /start to access the premium plans."
            )

