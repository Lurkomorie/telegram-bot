# Requirements Document

## Introduction

Упрощение системы подписок: переход от трёх уровней подписок (Plus, Pro, Legendary) к единой подписке с тремя периодами (день, неделя, месяц). Все периоды дают одинаковые преимущества, отличаются только длительностью и ценой со скидками.

## Glossary

- **Subscription_System**: Система управления подписками пользователей
- **Plans_Page**: Страница выбора и покупки подписок в miniapp
- **Premium_User**: Пользователь с активной подпиской любого периода
- **Stars**: Валюта Telegram для оплаты (⭐️)
- **Subscription_Period**: Период действия подписки (день, неделя, месяц)
- **Energy_System**: Система энергии, которая тратится только на создание персонажей

## Requirements

### Requirement 1: Единая подписка с тремя периодами

**User Story:** Как пользователь, я хочу выбрать период подписки из трёх вариантов, чтобы получить одинаковые преимущества на разный срок.

#### Acceptance Criteria

1. THE Subscription_System SHALL offer exactly three subscription periods: daily, weekly, and monthly
2. WHEN displaying subscription options, THE Plans_Page SHALL show the following prices:
   - Daily: 75 ⭐️ ($1.5) — без скидки
   - Weekly: 295 ⭐️ ($5.9) — старая цена 500 ⭐️ ($10), скидка 41%
   - Monthly: 495 ⭐️ ($9.9) — старая цена 2500 ⭐️, скидка 78%
3. WHEN displaying the monthly plan, THE Plans_Page SHALL show "Most Popular" badge above it
4. THE Subscription_System SHALL provide identical benefits for all subscription periods

### Requirement 2: Отображение скидок

**User Story:** Как пользователь, я хочу видеть размер скидки для каждого периода, чтобы понимать выгоду более длительных подписок.

#### Acceptance Criteria

1. WHEN displaying weekly subscription, THE Plans_Page SHALL show original price (500 ⭐️) crossed out and discount percentage (-41%)
2. WHEN displaying monthly subscription, THE Plans_Page SHALL show original price (2500 ⭐️) crossed out and discount percentage (-78%)
3. WHEN displaying daily subscription, THE Plans_Page SHALL NOT show any discount or crossed-out price
4. THE Plans_Page SHALL display discount percentages prominently near each discounted plan

### Requirement 3: Преимущества подписки

**User Story:** Как пользователь, я хочу видеть список преимуществ подписки один раз под всеми тарифами, чтобы не читать дублирующийся текст.

#### Acceptance Criteria

1. THE Plans_Page SHALL display subscription benefits in a single section below all plan options
2. THE Plans_Page SHALL display the following benefits with icons:
   - ♾️⚡️ Безлимитная энергия (бесплатное создание персонажей)
   - 🔞 Полное отсутствие блюра
   - 🎭 Улучшенные модели ИИ
   - 🧠 Улучшенная система памяти
   - ♻️ Улучшенная скорость генерации
   - ➕ Бонусы в создании персонажа
   - 💬 Увеличен лимит символов в описании до 4000
3. THE Plans_Page SHALL show "💸 Преимущества 👇🏻" header above the benefits list
4. THE Plans_Page SHALL NOT duplicate benefits text for each subscription period

### Requirement 7: Новая система энергии

**User Story:** Как пользователь, я хочу понимать на что тратится энергия, чтобы планировать использование приложения.

#### Acceptance Criteria

1. THE Energy_System SHALL consume energy ONLY for character creation
2. THE Energy_System SHALL NOT consume energy for messages, photos, or other actions
3. WHEN a user has premium subscription, THE Energy_System SHALL provide unlimited energy (free character creation)
4. WHEN a free user creates a character, THE Energy_System SHALL deduct energy cost from their balance
5. THE Plans_Page SHALL clearly communicate that premium users get free character creation

### Requirement 4: Новая структура UI

**User Story:** Как пользователь, я хочу видеть сначала все тарифы с ценами, а затем общий список преимуществ, чтобы быстро сравнить цены и понять что я получу.

#### Acceptance Criteria

1. THE Plans_Page SHALL display subscription periods as selectable cards at the top
2. WHEN a subscription period is selected, THE Plans_Page SHALL highlight it with a checkmark
3. THE Plans_Page SHALL display benefits section below all subscription cards
4. THE Plans_Page SHALL show a sticky purchase button at the bottom
5. THE Plans_Page SHALL remove the tabs for "Token Packages" and "Premium Tiers" and show only unified subscriptions

### Requirement 5: Локализация

**User Story:** Как пользователь, я хочу видеть информацию о подписках на своём языке, чтобы понимать условия.

#### Acceptance Criteria

1. THE Plans_Page SHALL display all subscription text in Russian for ru locale
2. THE Plans_Page SHALL display all subscription text in English for en locale
3. WHEN displaying period names, THE Subscription_System SHALL use localized strings:
   - Daily: "День" / "Day"
   - Weekly: "Неделя" / "Week"  
   - Monthly: "Месяц" / "Month"
4. THE Plans_Page SHALL localize all benefit descriptions

### Requirement 6: Удаление старой системы

**User Story:** Как разработчик, я хочу удалить старую систему с токенами и тремя уровнями подписок, чтобы упростить кодовую базу.

#### Acceptance Criteria

1. THE Subscription_System SHALL remove token packages purchasing functionality
2. THE Subscription_System SHALL remove Plus, Pro, Legendary tier distinctions
3. THE Plans_Page SHALL NOT display token packages tab
4. THE Subscription_System SHALL treat all premium users equally regardless of previous tier
