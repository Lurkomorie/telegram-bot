# Implementation Plan: Unified Subscription System

## Overview

Реализация упрощённой системы подписок: удаление токенов и трёх уровней, переход к единой подписке с тремя периодами (день, неделя, месяц).

## Tasks

- [x] 1. Обновить бэкенд платежей
  - [x] 1.1 Обновить PAYMENT_PRODUCTS в payment.py
    - Удалить все token packages (tokens_50, tokens_100, etc.)
    - Удалить старые tier subscriptions (plus_month, pro_month, legendary_month, etc.)
    - Добавить новые subscription products: subscription_daily (75⭐️), subscription_weekly (295⭐️), subscription_monthly (495⭐️)
    - _Requirements: 1.2, 6.1, 6.2_
  - [x] 1.2 Обновить process_payment_transaction для новых подписок
    - Обработка type="subscription" вместо type="tier"
    - Все подписки активируют одинаковый премиум статус
    - _Requirements: 1.4, 6.4_
  - [x] 1.3 Написать unit тесты для новых payment products
    - Проверить цены соответствуют спецификации
    - Проверить duration для каждого периода
    - _Requirements: 1.2_

- [x] 2. Обновить систему энергии
  - [x] 2.1 Изменить логику потребления энергии
    - Энергия тратится ТОЛЬКО на создание персонажей
    - Удалить списание энергии за сообщения/фото
    - _Requirements: 7.1, 7.2_
  - [x] 2.2 Обновить создание персонажей для премиум пользователей
    - Премиум пользователи не тратят энергию на создание
    - Бесплатные пользователи платят энергией
    - _Requirements: 7.3, 7.4_
  - [x] 2.3 Написать property тест для энергии
    - **Property 5: Energy Consumption Only For Character Creation**
    - **Validates: Requirements 7.1, 7.2**

- [x] 3. Checkpoint - Проверить бэкенд
  - Убедиться что все тесты проходят, спросить пользователя если есть вопросы

- [-] 4. Обновить фронтенд PlansPage
  - [x] 4.1 Переписать PlansPage.jsx
    - Удалить табы (tokens/tiers)
    - Создать карточки подписок с ценами и скидками
    - Добавить "Most Popular" badge на месячный план
    - Добавить секцию преимуществ под карточками
    - _Requirements: 1.1, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5_
  - [x] 4.2 Обновить PlansPage.css
    - Стили для новых карточек подписок
    - Стили для скидок и зачёркнутых цен
    - Стили для секции преимуществ
    - _Requirements: 2.4, 4.1_

- [x] 5. Обновить локализацию
  - [x] 5.1 Обновить ru.json
    - Добавить ключи для периодов: subscription.period.day, subscription.period.week, subscription.period.month
    - Добавить ключи для преимуществ: subscription.benefits.*
    - Добавить заголовок преимуществ
    - _Requirements: 5.1, 5.3, 5.4_
  - [x] 5.2 Обновить en.json
    - Те же ключи на английском
    - _Requirements: 5.2, 5.3, 5.4_
  - [-] 5.3 Написать property тест для локализации (пропущено по запросу)
    - **Property 4: Localization Completeness**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

- [x] 6. Удалить старый код
  - [x] 6.1 Удалить неиспользуемые компоненты
    - PlansPage.jsx полностью переписан - старый код удалён
    - CSS обновлён для новой структуры
    - _Requirements: 6.1, 6.2, 6.3_
  - [-] 6.2 Очистить локализацию (оставлено для обратной совместимости)
    - Старые ключи premium.plus/pro/legendary могут использоваться в других местах
    - _Requirements: 6.1, 6.2_

- [x] 7. Final Checkpoint - Финальная проверка
  - Все файлы обновлены без ошибок
  - PlansPage.jsx - новая структура с 3 периодами подписки
  - PlansPage.css - стили для subscription-card, benefits-section
  - ru.json/en.json - добавлены ключи subscription.*
  - Бэкенд payment.py - новые PAYMENT_PRODUCTS
  - Энергия тратится только на создание персонажей

## Notes

- Каждая задача ссылается на конкретные требования для трассируемости
- Checkpoints обеспечивают инкрементальную валидацию
- Property тесты валидируют универсальные свойства корректности
