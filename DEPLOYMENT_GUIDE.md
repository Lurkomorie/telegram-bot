# 🚀 Подготовка к Production Deploy: Premium Features

## 📋 Что было сделано

### 1. Анализ состояния

- ✅ Проверил production базу данных (3,741 пользователей, 5 активных премиумов)
- ✅ Обнаружил и исправил проблемы с миграциями
- ✅ Выявил недостающие поля в production БД

### 2. Исправление миграций

- ✅ **Удален дубликат:** `app/db/migrations/versions/021_add_system_messages.py` (был дубликатом 025)
- ✅ **Создана новая миграция:** `app/db/migrations/versions/026_add_missing_user_fields.py`
  - Добавит `temp_energy` (ежедневные бесплатные токены для премиумов)
  - Добавит `last_temp_energy_refill` (дата последнего пополнения)
  - Добавит `char_created` (флаг создания первого персонажа)
  - Миграция безопасная - проверяет существование полей перед добавлением

### 3. Созданы скрипты

#### `scripts/check_prod_before_deploy.py`

Проверяет состояние production БД перед деплоем:

- Какие колонки есть в users table
- Сколько премиум пользователей
- Текущая версия миграции
- Сколько токенов будет начислено

#### `scripts/grant_premium_tokens_after_deploy.py`

Начисляет токены премиум пользователям ПОСЛЕ деплоя:

- **+500 постоянных токенов** каждому премиум пользователю (разовый бонус)
- **Инициализирует temp_energy** по tier (Plus: 50, Premium: 75, Pro: 100, Legendary: 200)
- Устанавливает `last_temp_energy_refill` чтобы scheduler работал
- Имеет режим `--dry-run` для безопасной проверки

#### `scripts/verify_premium_users_before_deploy.py`

Проверка премиум пользователей (имеет проблемы с импортами, используй вместо него `check_prod_before_deploy.py`)

---

## 🎯 Что нужно сделать ТЕБЕ

### ШАГ 1: Коммит изменений в development

```bash
cd /Users/artemtrifanuk/Documents/telegram-bot

# Проверь что изменилось
git status

# Должно быть:
# deleted: app/db/migrations/versions/021_add_system_messages.py
# new file: app/db/migrations/versions/026_add_missing_user_fields.py
# new file: scripts/check_prod_before_deploy.py
# new file: scripts/grant_premium_tokens_after_deploy.py
# modified: scripts/verify_premium_users_before_deploy.py

# Добавь все
git add -A

# Коммит
git commit -m "Fix: remove duplicate migration 021, add migration 026 for missing fields, add deployment scripts"

# Пуш в development
git push origin development
```

### ШАГ 2: Проверка перед деплоем

```bash
# Проверь текущее состояние production
python scripts/check_prod_before_deploy.py

# Ожидаемый вывод:
# - Total users: 3741
# - Active premium: 5
# - Current migration: 024
# - Missing fields: temp_energy, last_temp_energy_refill, char_created
```

### ШАГ 3: Создай БЭКАП БД (КРИТИЧЕСКИ ВАЖНО!)

```bash
# Railway
railway run pg_dump > backup_before_premium_$(date +%Y%m%d_%H%M%S).sql

# Или Heroku
heroku pg:backups:capture --app your-app-name

# ПРОВЕРЬ что файл создался и не пустой!
ls -lh backup_before_premium_*.sql
# Должен быть > 1 MB
```

**⚠️ БЕЗ БЭКАПА НЕ ПРОДОЛЖАЙ!**

### ШАГ 4: Мердж в main (запустит деплой)

```bash
# Переключись на main
git checkout main
git pull origin main

# Смерджи development
git merge development --no-ff -m "Merge premium features: tier system, tokens, referrals, system messages"

# Проверь что все ок
git log --oneline -5

# ВНИМАНИЕ: Этот пуш запустит автоматический деплой!
git push origin main
```

### ШАГ 5: Мониторинг деплоя (следи за логами!)

```bash
# Railway
railway logs --tail

# Или Heroku
heroku logs --tail --app your-app-name

# ЧТО ИСКАТЬ:
# ✅ "Running migrations..."
# ✅ "Migration 024 -> a38ea596e306"
# ✅ "Migration a38ea596e306 -> 0296caa64d7d"
# ✅ "Migration 0296caa64d7d -> 026"
# ✅ "Added temp_energy column"
# ✅ "Added last_temp_energy_refill column"
# ✅ "Added char_created column"
# ❌ Любые ERROR, Exception, Failed
```

### ШАГ 6: Проверка после деплоя

```bash
# Проверь версию миграции (должна быть 026)
railway run python -c "
from sqlalchemy import create_engine, text
from app.settings import settings
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    print('Migration version:', result.fetchone()[0])
"

# Проверь что поля добавились
railway run python scripts/check_prod_before_deploy.py
# Теперь temp_energy и другие должны показывать "EXISTS"
```

### ШАГ 7: Начисли токены премиум пользователям

```bash
# СНАЧАЛА dry-run для проверки
railway run python scripts/grant_premium_tokens_after_deploy.py --dry-run

# Ожидаемый вывод:
# Found 5 active premium users
# Would grant 500 tokens to each
# Would initialize temp_energy based on tier
# Total: 2,500 permanent tokens + temp_energy initialization

# Если все выглядит правильно - запусти реально
railway run python scripts/grant_premium_tokens_after_deploy.py

# Скрипт спросит подтверждение - напиши 'yes'
```

### ШАГ 8: Smoke Test (проверь что все работает)

**В Telegram как премиум пользователь:**

1. Открой бота
2. Проверь что премиум статус отображается ✅
3. Проверь баланс токенов (должно быть +500) ✅
4. Отправь сообщение - должно работать ✅

**В Telegram как новый пользователь:**

1. /start бота
2. Free tier должен работать ✅
3. Премиум опции должны быть видны ✅

**Mini App:**

1. Открой mini app из бота
2. Проверь что загружается ✅
3. Токены отображаются правильно ✅
4. Можно зайти в премиум секции ✅

### ШАГ 9: Финальная проверка (через 30 минут)

```bash
# Проверь что токены начислились
railway run python -c "
from sqlalchemy import create_engine, text
from app.settings import settings
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT id, username, energy, temp_energy, premium_tier
        FROM users
        WHERE is_premium = true
          AND (premium_until IS NULL OR premium_until > NOW())
        ORDER BY id
        LIMIT 10
    '''))
    print('Premium users after token grant:')
    print(f'{\"ID\":<12} {\"Username\":<20} {\"Energy\":<10} {\"TempEnergy\":<12} {\"Tier\":<10}')
    print('-' * 70)
    for row in result:
        user_id, username, energy, temp_energy, tier = row
        print(f'{user_id:<12} @{(username or \"no_username\"):<19} {energy:<10} {temp_energy:<12} {tier:<10}')
"

# Проверь логи на ошибки
railway logs --tail | grep -i error
# Должно быть пусто или минимум ошибок
```

---

## 📊 Что получат премиум пользователи

### Существующие 5 премиум пользователей получат:

**1. Постоянные токены (разово):**

- +500 токенов каждому
- Всего: 2,500 токенов

**2. Temp Energy (ежедневные токены):**

- Зависит от их tier:
  - Plus: 50/день
  - Premium: 75/день
  - Pro: 100/день
  - Legendary: 200/день
- **Автоматически пополняется каждый день!**
- Тратится В ПЕРВУЮ ОЧЕРЕДЬ перед постоянными токенами

**Пример:** Если все на tier "Premium":

- Каждый получит 500 + 75 = **575 токенов сразу**
- Потом каждый день автоматически +75 temp_energy
- За месяц: 500 постоянных + (75 × 30) = **2,750 токенов минимум**

---

## 🆘 Если что-то пошло не так

### Проблема: Миграция упала с ошибкой

```bash
# Смотри логи
railway logs --tail

# Проверь на какой миграции застряло
railway run python -c "
from sqlalchemy import create_engine, text
from app.settings import settings
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    print('Current migration:', result.fetchone()[0])
"

# Попробуй запустить миграции вручную
railway run alembic upgrade head
```

### Проблема: Поля temp_energy не добавились

```bash
# Добавь вручную через SQL
railway run python -c "
from sqlalchemy import create_engine, text
from app.settings import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    # temp_energy
    try:
        conn.execute(text('ALTER TABLE users ADD COLUMN temp_energy BIGINT NOT NULL DEFAULT 0'))
        conn.commit()
        print('✅ Added temp_energy')
    except Exception as e:
        print(f'temp_energy: {e}')

    # last_temp_energy_refill
    try:
        conn.execute(text('ALTER TABLE users ADD COLUMN last_temp_energy_refill TIMESTAMP'))
        conn.commit()
        print('✅ Added last_temp_energy_refill')
    except Exception as e:
        print(f'last_temp_energy_refill: {e}')

    # char_created
    try:
        conn.execute(text('ALTER TABLE users ADD COLUMN char_created BOOLEAN NOT NULL DEFAULT false'))
        conn.commit()
        print('✅ Added char_created')
    except Exception as e:
        print(f'char_created: {e}')
"
```

### Проблема: Все сломалось, нужен откат

```bash
# 1. Найди merge commit
git log --oneline -5

# 2. Реверт мерджа (создаст новый коммит отменяющий изменения)
git revert -m 1 <merge-commit-hash>
git push origin main

# 3. ЕСЛИ НУЖНО - восстанови БД из бэкапа (потеряешь данные после бэкапа!)
psql $DATABASE_URL < backup_before_premium_*.sql

# Или через Railway
railway run psql < backup_before_premium_*.sql
```

---

## 🔍 Как работает temp_energy (для понимания)

**temp_energy** - ежедневные бесплатные токены для премиумов:

1. **При активации премиума:**

   - Юзер получает разовый бонус (500 токенов в `energy`)
   - Получает первую порцию `temp_energy` по tier
   - Устанавливается `last_temp_energy_refill = now()`

2. **Каждый день автоматически (scheduler):**

   - Проверяется прошло ли 24 часа с `last_temp_energy_refill`
   - Если да - `temp_energy` сбрасывается до значения tier
   - Обновляется `last_temp_energy_refill`

3. **При использовании токенов:**

   - Сначала тратится `temp_energy`
   - Когда `temp_energy = 0`, тратится постоянный `energy`

4. **Не накапливается:**
   - Каждый день temp_energy **сбрасывается** (не прибавляется!)
   - Не использовал сегодня - потерял

**Зачем:** Мотивирует ежедневное использование + предсказуемые расходы.

---

## ✅ Чеклист готовности

**Перед началом:**

- [ ] Development branch актуален
- [ ] Все изменения закоммичены
- [ ] Скрипты проверены локально

**Перед деплоем:**

- [ ] Бэкап БД создан и проверен
- [ ] Проверка production состояния выполнена
- [ ] Все выглядит правильно

**Во время деплоя:**

- [ ] Мердж в main выполнен
- [ ] Логи отслеживаются в реальном времени
- [ ] Миграции прошли успешно

**После деплоя:**

- [ ] Версия миграции = 026
- [ ] Все поля добавились (temp_energy, char_created, last_temp_energy_refill)
- [ ] Токены начислены всем премиумам (+500 каждому)
- [ ] Temp_energy инициализирован
- [ ] Smoke test пройден
- [ ] Логи чистые (нет критичных ошибок)
- [ ] Пользователи счастливы 😊

---

## 📁 Созданные файлы

### Миграции

- `app/db/migrations/versions/026_add_missing_user_fields.py` - добавляет недостающие поля

### Скрипты

- `scripts/check_prod_before_deploy.py` - проверка production перед деплоем
- `scripts/grant_premium_tokens_after_deploy.py` - начисление токенов после деплоя
- `scripts/verify_premium_users_before_deploy.py` - старый скрипт (работает с ORM, может падать)

### Удаленные файлы

- `app/db/migrations/versions/021_add_system_messages.py` - дубликат (удален)

---

## 🎯 Итого

**Изменения в БД после деплоя:**

- Миграция с 024 на 026
- +3 новых поля в users table
- Все system messages таблицы уже были (созданы ранее)
- Payment_transactions таблица уже была

**Изменения для пользователей:**

- 5 премиум пользователей получат +500 токенов
- Каждый получит temp_energy по своему tier
- Дальше каждый день будут получать автоматически temp_energy

**Риски:** 🟡 Средние

- Много изменений в БД, но есть бэкап
- Миграции протестированы и безопасные
- Можно откатить если что-то пойдет не так

**Время деплоя:** ~30-60 минут (включая проверки)

---

**Создано:** 1 декабря 2025  
**Автор:** AI Assistant  
**Статус:** ✅ Готово к деплою

**Вопросы?** Напиши если что-то непонятно!

**Удачи с деплоем!** 🚀
