#!/usr/bin/env python3
"""
Seed miniapp translations into the database

This script adds all hardcoded Russian text translations from miniapp components
to the unified Translation table.

Usage:
    python scripts/seed_miniapp_translations.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import get_db
from app.db import crud
from app.db.models import Translation


def seed_miniapp_translations():
    """Insert miniapp translations into database"""
    print("=" * 70)
    print("MINIAPP TRANSLATIONS SEEDER")
    print("=" * 70)
    print("\n📝 Inserting translations into database...")
    
    translations = [
        # App.jsx - Headers
        {"key": "miniapp.app.header.premium", "lang": "ru", "value": "Премиум", "category": "miniapp"},
        {"key": "miniapp.app.header.premium", "lang": "en", "value": "Premium", "category": "miniapp"},
        {"key": "miniapp.app.header.energy", "lang": "ru", "value": "Энергия", "category": "miniapp"},
        {"key": "miniapp.app.header.energy", "lang": "en", "value": "Energy", "category": "miniapp"},
        {"key": "miniapp.app.header.referrals", "lang": "ru", "value": "Рефералы", "category": "miniapp"},
        {"key": "miniapp.app.header.referrals", "lang": "en", "value": "Referrals", "category": "miniapp"},
        {"key": "miniapp.app.header.checkoutTitle", "lang": "ru", "value": "Покупка {icon} {name}", "category": "miniapp"},
        {"key": "miniapp.app.header.checkoutTitle", "lang": "en", "value": "Purchase {icon} {name}", "category": "miniapp"},
        
        # App.jsx - Subscription texts
        {"key": "miniapp.app.subscriptionTexts.coolFeatures", "lang": "ru", "value": "Крутые фичи", "category": "miniapp"},
        {"key": "miniapp.app.subscriptionTexts.coolFeatures", "lang": "en", "value": "Cool Features", "category": "miniapp"},
        {"key": "miniapp.app.subscriptionTexts.recommendBuy", "lang": "ru", "value": "Рекомендуем купить", "category": "miniapp"},
        {"key": "miniapp.app.subscriptionTexts.recommendBuy", "lang": "en", "value": "We Recommend", "category": "miniapp"},
        {"key": "miniapp.app.subscriptionTexts.tryIt", "lang": "ru", "value": "Попробуйте", "category": "miniapp"},
        {"key": "miniapp.app.subscriptionTexts.tryIt", "lang": "en", "value": "Try It", "category": "miniapp"},
        
        # App.jsx - Daily bonus
        {"key": "miniapp.app.dailyBonus.referralBonus", "lang": "ru", "value": "Бонус за друга", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.referralBonus", "lang": "en", "value": "Friend Bonus", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.gift", "lang": "ru", "value": "Подарок", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.gift", "lang": "en", "value": "Gift", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.day", "lang": "ru", "value": "День {day}", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.day", "lang": "en", "value": "Day {day}", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.clickToClaim", "lang": "ru", "value": "Нажмите чтобы забрать", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.clickToClaim", "lang": "en", "value": "Click to claim", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.subscription", "lang": "ru", "value": "Подписка", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.subscription", "lang": "en", "value": "Subscription", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.alreadyClaimed", "lang": "ru", "value": "Бонус уже получен! Следующий через {hours}ч {minutes}м", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.alreadyClaimed", "lang": "en", "value": "Bonus already claimed! Next in {hours}h {minutes}m", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.claimFailed", "lang": "ru", "value": "Не удалось получить бонус", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.claimFailed", "lang": "en", "value": "Failed to claim bonus", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.claimError", "lang": "ru", "value": "Ошибка при получении бонуса. Попробуйте снова.", "category": "miniapp"},
        {"key": "miniapp.app.dailyBonus.claimError", "lang": "en", "value": "Error claiming bonus. Please try again.", "category": "miniapp"},
        
        # App.jsx - Time
        {"key": "miniapp.app.time.hours", "lang": "ru", "value": "ч", "category": "miniapp"},
        {"key": "miniapp.app.time.hours", "lang": "en", "value": "h", "category": "miniapp"},
        {"key": "miniapp.app.time.minutes", "lang": "ru", "value": "м", "category": "miniapp"},
        {"key": "miniapp.app.time.minutes", "lang": "en", "value": "m", "category": "miniapp"},
        
        # CheckoutPage.jsx
        {"key": "miniapp.checkout.paymentMethod", "lang": "ru", "value": "СПОСОБ ОПЛАТЫ", "category": "miniapp"},
        {"key": "miniapp.checkout.paymentMethod", "lang": "en", "value": "PAYMENT METHOD", "category": "miniapp"},
        {"key": "miniapp.checkout.payWithStars", "lang": "ru", "value": "Звёздами", "category": "miniapp"},
        {"key": "miniapp.checkout.payWithStars", "lang": "en", "value": "Stars", "category": "miniapp"},
        {"key": "miniapp.checkout.period", "lang": "ru", "value": "ПЕРИОД", "category": "miniapp"},
        {"key": "miniapp.checkout.period", "lang": "en", "value": "PERIOD", "category": "miniapp"},
        {"key": "miniapp.checkout.periodMonth", "lang": "ru", "value": "Месяц", "category": "miniapp"},
        {"key": "miniapp.checkout.periodMonth", "lang": "en", "value": "Month", "category": "miniapp"},
        {"key": "miniapp.checkout.period3Months", "lang": "ru", "value": "3 месяца", "category": "miniapp"},
        {"key": "miniapp.checkout.period3Months", "lang": "en", "value": "3 months", "category": "miniapp"},
        {"key": "miniapp.checkout.period6Months", "lang": "ru", "value": "6 месяцев", "category": "miniapp"},
        {"key": "miniapp.checkout.period6Months", "lang": "en", "value": "6 months", "category": "miniapp"},
        {"key": "miniapp.checkout.totalLabel", "lang": "ru", "value": "К оплате", "category": "miniapp"},
        {"key": "miniapp.checkout.totalLabel", "lang": "en", "value": "Total", "category": "miniapp"},
        {"key": "miniapp.checkout.stars", "lang": "ru", "value": "звёзд", "category": "miniapp"},
        {"key": "miniapp.checkout.stars", "lang": "en", "value": "stars", "category": "miniapp"},
        {"key": "miniapp.checkout.processing", "lang": "ru", "value": "Обработка...", "category": "miniapp"},
        {"key": "miniapp.checkout.processing", "lang": "en", "value": "Processing...", "category": "miniapp"},
        {"key": "miniapp.checkout.payButton", "lang": "ru", "value": "Оплатить", "category": "miniapp"},
        {"key": "miniapp.checkout.payButton", "lang": "en", "value": "Pay", "category": "miniapp"},
        {"key": "miniapp.checkout.subscriptionSuccess", "lang": "ru", "value": "✅ Подписка успешно оформлена! Спасибо за покупку!", "category": "miniapp"},
        {"key": "miniapp.checkout.subscriptionSuccess", "lang": "en", "value": "✅ Subscription successful! Thank you for your purchase!", "category": "miniapp"},
        {"key": "miniapp.checkout.paymentCancelled", "lang": "ru", "value": "Оплата отменена", "category": "miniapp"},
        {"key": "miniapp.checkout.paymentCancelled", "lang": "en", "value": "Payment cancelled", "category": "miniapp"},
        {"key": "miniapp.checkout.paymentFailed", "lang": "ru", "value": "Ошибка оплаты. Попробуйте снова.", "category": "miniapp"},
        {"key": "miniapp.checkout.paymentFailed", "lang": "en", "value": "Payment failed. Please try again.", "category": "miniapp"},
        {"key": "miniapp.checkout.invoiceFailed", "lang": "ru", "value": "Не удалось создать счёт. Попробуйте снова.", "category": "miniapp"},
        {"key": "miniapp.checkout.invoiceFailed", "lang": "en", "value": "Failed to create invoice. Please try again.", "category": "miniapp"},
        
        # PremiumPage.jsx
        {"key": "miniapp.premium.benefits", "lang": "ru", "value": "Преимущества", "category": "miniapp"},
        {"key": "miniapp.premium.benefits", "lang": "en", "value": "Benefits", "category": "miniapp"},
        {"key": "miniapp.premium.perMonth", "lang": "ru", "value": "/ месяц", "category": "miniapp"},
        {"key": "miniapp.premium.perMonth", "lang": "en", "value": "/ month", "category": "miniapp"},
        {"key": "miniapp.premium.getButton", "lang": "ru", "value": "Получить {name}", "category": "miniapp"},
        {"key": "miniapp.premium.getButton", "lang": "en", "value": "Get {name}", "category": "miniapp"},
        
        # PremiumPage.jsx - Plus features
        {"key": "miniapp.premium.plus.feature1", "lang": "ru", "value": "Бесплатные 25 токенов каждый день", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature1", "lang": "en", "value": "Free 25 tokens every day", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature2", "lang": "ru", "value": "Улучшенная модель ИИ", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature2", "lang": "en", "value": "Enhanced AI model", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature3", "lang": "ru", "value": "Дешёвая генерация фотографий", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature3", "lang": "en", "value": "Cheap photo generation", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature4", "lang": "ru", "value": "Скачивание фотографий", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature4", "lang": "en", "value": "Photo downloads", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature5", "lang": "ru", "value": "Свои обои в чате", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature5", "lang": "en", "value": "Custom chat wallpapers", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature6", "lang": "ru", "value": "Генерация голосовых сообщений", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature6", "lang": "en", "value": "Voice message generation", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature7", "lang": "ru", "value": "Создание фотографий по описанию", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature7", "lang": "en", "value": "Create photos from text", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature8", "lang": "ru", "value": "Нет никаких ограничений", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature8", "lang": "en", "value": "No limitations", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature9", "lang": "ru", "value": "Дешевле создание персонажа в мастерской", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature9", "lang": "en", "value": "Cheaper character creation in workshop", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature10", "lang": "ru", "value": "Увеличен лимит до 4,000 символов в описании персонажа", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature10", "lang": "en", "value": "Increased limit to 4,000 characters in character description", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature11", "lang": "ru", "value": "Отправка голосовых сообщений до 30 секунд", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature11", "lang": "en", "value": "Send voice messages up to 30 seconds", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature12", "lang": "ru", "value": "Создание групповых чатов", "category": "miniapp"},
        {"key": "miniapp.premium.plus.feature12", "lang": "en", "value": "Create group chats", "category": "miniapp"},
        
        # PremiumPage.jsx - Pro features
        {"key": "miniapp.premium.pro.feature1", "lang": "ru", "value": "Всё что в Plus, а так же", "category": "miniapp"},
        {"key": "miniapp.premium.pro.feature1", "lang": "en", "value": "Everything in Plus, plus", "category": "miniapp"},
        {"key": "miniapp.premium.pro.feature2", "lang": "ru", "value": "Бесплатные 75 токенов каждый день", "category": "miniapp"},
        {"key": "miniapp.premium.pro.feature2", "lang": "en", "value": "Free 75 tokens every day", "category": "miniapp"},
        {"key": "miniapp.premium.pro.feature3", "lang": "ru", "value": "Отправка голосовых сообщений до 90 секунд", "category": "miniapp"},
        {"key": "miniapp.premium.pro.feature3", "lang": "en", "value": "Send voice messages up to 90 seconds", "category": "miniapp"},
        
        # PremiumPage.jsx - Legendary features
        {"key": "miniapp.premium.legendary.feature1", "lang": "ru", "value": "Всё что в Premium, а так же", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature1", "lang": "en", "value": "Everything in Premium, plus", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature2", "lang": "ru", "value": "Бесплатные 100 токенов каждый день", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature2", "lang": "en", "value": "Free 100 tokens every day", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature3", "lang": "ru", "value": "Отправка голосовых сообщений до 120 секунд", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature3", "lang": "en", "value": "Send voice messages up to 120 seconds", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature4", "lang": "ru", "value": "Генерация анимаций из фотографии", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature4", "lang": "en", "value": "Generate animations from photos", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature5", "lang": "ru", "value": "Генерация видео сообщений", "category": "miniapp"},
        {"key": "miniapp.premium.legendary.feature5", "lang": "en", "value": "Generate video messages", "category": "miniapp"},
        
        # SettingsPage.jsx
        {"key": "miniapp.settings.premiumSubscriptions", "lang": "ru", "value": "Премиум подписки", "category": "miniapp"},
        {"key": "miniapp.settings.premiumSubscriptions", "lang": "en", "value": "Premium Subscriptions", "category": "miniapp"},
        {"key": "miniapp.settings.friends", "lang": "ru", "value": "Друзья", "category": "miniapp"},
        {"key": "miniapp.settings.friends", "lang": "en", "value": "Friends", "category": "miniapp"},
        {"key": "miniapp.settings.buyEnergy", "lang": "ru", "value": "Купить энергию", "category": "miniapp"},
        {"key": "miniapp.settings.buyEnergy", "lang": "en", "value": "Buy Energy", "category": "miniapp"},
        
        # TokensPage.jsx
        {"key": "miniapp.tokens.tokensAdded", "lang": "ru", "value": "✅ Токены успешно добавлены! Спасибо за покупку!", "category": "miniapp"},
        {"key": "miniapp.tokens.tokensAdded", "lang": "en", "value": "✅ Tokens successfully added! Thank you for your purchase!", "category": "miniapp"},
        {"key": "miniapp.tokens.paymentCancelled", "lang": "ru", "value": "Оплата отменена", "category": "miniapp"},
        {"key": "miniapp.tokens.paymentCancelled", "lang": "en", "value": "Payment cancelled", "category": "miniapp"},
        {"key": "miniapp.tokens.paymentFailed", "lang": "ru", "value": "Ошибка оплаты. Попробуйте снова.", "category": "miniapp"},
        {"key": "miniapp.tokens.paymentFailed", "lang": "en", "value": "Payment failed. Please try again.", "category": "miniapp"},
        {"key": "miniapp.tokens.invoiceFailed", "lang": "ru", "value": "Не удалось создать счёт. Попробуйте снова.", "category": "miniapp"},
        {"key": "miniapp.tokens.invoiceFailed", "lang": "en", "value": "Failed to create invoice. Please try again.", "category": "miniapp"},
        {"key": "miniapp.tokens.stars", "lang": "ru", "value": "звёзд", "category": "miniapp"},
        {"key": "miniapp.tokens.stars", "lang": "en", "value": "stars", "category": "miniapp"},
        {"key": "miniapp.tokens.processing", "lang": "ru", "value": "Обработка...", "category": "miniapp"},
        {"key": "miniapp.tokens.processing", "lang": "en", "value": "Processing...", "category": "miniapp"},
        {"key": "miniapp.tokens.buyButton", "lang": "ru", "value": "Купить энергию", "category": "miniapp"},
        {"key": "miniapp.tokens.buyButton", "lang": "en", "value": "Buy Energy", "category": "miniapp"},
        
        # ReferralsPage.jsx
        {"key": "miniapp.referrals.title", "lang": "ru", "value": "Превращай друзей в токены!", "category": "miniapp"},
        {"key": "miniapp.referrals.title", "lang": "en", "value": "Turn friends into tokens!", "category": "miniapp"},
        {"key": "miniapp.referrals.earn", "lang": "ru", "value": "Зарабатывай", "category": "miniapp"},
        {"key": "miniapp.referrals.earn", "lang": "en", "value": "Earn", "category": "miniapp"},
        {"key": "miniapp.referrals.tokensAmount", "lang": "ru", "value": "50 токенов", "category": "miniapp"},
        {"key": "miniapp.referrals.tokensAmount", "lang": "en", "value": "50 tokens", "category": "miniapp"},
        {"key": "miniapp.referrals.perFriend", "lang": "ru", "value": "с каждого друга", "category": "miniapp"},
        {"key": "miniapp.referrals.perFriend", "lang": "en", "value": "per friend", "category": "miniapp"},
        {"key": "miniapp.referrals.statsTitle", "lang": "ru", "value": "Рефералы", "category": "miniapp"},
        {"key": "miniapp.referrals.statsTitle", "lang": "en", "value": "Referrals", "category": "miniapp"},
        {"key": "miniapp.referrals.friendsInvited", "lang": "ru", "value": "Друзей приглашено", "category": "miniapp"},
        {"key": "miniapp.referrals.friendsInvited", "lang": "en", "value": "Friends invited", "category": "miniapp"},
        {"key": "miniapp.referrals.note", "lang": "ru", "value": "Друг должен перейти по вашей ссылке и зайти в приложение чтобы получить токены", "category": "miniapp"},
        {"key": "miniapp.referrals.note", "lang": "en", "value": "Your friend must use your link and open the app to earn tokens", "category": "miniapp"},
        {"key": "miniapp.referrals.opening", "lang": "ru", "value": "Открытие...", "category": "miniapp"},
        {"key": "miniapp.referrals.opening", "lang": "en", "value": "Opening...", "category": "miniapp"},
        {"key": "miniapp.referrals.inviteButton", "lang": "ru", "value": "Пригласить друга", "category": "miniapp"},
        {"key": "miniapp.referrals.inviteButton", "lang": "en", "value": "Invite a friend", "category": "miniapp"},
        {"key": "miniapp.referrals.linkCopiedTitle", "lang": "ru", "value": "Ссылка скопирована!", "category": "miniapp"},
        {"key": "miniapp.referrals.linkCopiedTitle", "lang": "en", "value": "Link copied!", "category": "miniapp"},
        {"key": "miniapp.referrals.linkCopiedMessage", "lang": "ru", "value": "Реферальная ссылка скопирована в буфер обмена", "category": "miniapp"},
        {"key": "miniapp.referrals.linkCopiedMessage", "lang": "en", "value": "Referral link copied to clipboard", "category": "miniapp"},
        {"key": "miniapp.referrals.copyFailed", "lang": "ru", "value": "Не удалось скопировать ссылку", "category": "miniapp"},
        {"key": "miniapp.referrals.copyFailed", "lang": "en", "value": "Failed to copy link", "category": "miniapp"},
    ]
    
    with get_db() as db:
        count = 0
        
        for trans in translations:
            crud.create_or_update_translation(
                db,
                key=trans["key"],
                lang=trans["lang"],
                value=trans["value"],
                category=trans["category"]
            )
            count += 1
        
        print(f"✅ Processed {len(translations)} translations (created or updated)")
    
    print("\n" + "=" * 70)
    print("✨ SEEDING COMPLETE!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("   1. Run: python scripts/generate_miniapp_translations.py")
    print("   2. Update miniapp components to use t() function")
    print("   3. Rebuild miniapp: cd miniapp && npm run build")
    print()


def main():
    try:
        seed_miniapp_translations()
    except Exception as e:
        print(f"\n❌ Error seeding translations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

