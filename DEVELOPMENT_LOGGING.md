# Development Logging Guide

## Overview

Система детального логирования для разработки, которая активируется автоматически при установке `ENVIRONMENT=development`.

## Включение Development Режима

Добавьте в `.env` файл:

```bash
ENVIRONMENT=development
```

Или установите переменную окружения:

```bash
export ENVIRONMENT=development
```

## Что Логируется

### 1. Pipeline Timing (Замер Времени)

Каждый запрос проходит через пайплайн с автоматическим замером времени для каждого этапа:

**Пример вывода:**

```
================================================================================
[PIPELINE-TIMER] ⏱️  Starting: Message Pipeline (Chat: abc-123...)
================================================================================

[PIPELINE-TIMER] ▶️  Initialization
[PIPELINE-TIMER] ✅ Initialization: 125.43ms (0.13s)

[PIPELINE-TIMER] ▶️  Batch #1: Get Messages from Queue
[PIPELINE-TIMER] ⚡ Batch #1: Get Messages from Queue: 15.23ms (0.02s)

[PIPELINE-TIMER] ▶️  Batch #1: Process Messages
[PIPELINE-TIMER] ▶️  Start Typing Indicator
[PIPELINE-TIMER] ⚡ Start Typing Indicator: 45.67ms (0.05s)

[PIPELINE-TIMER] ▶️  Fetch Data from Database
[PIPELINE-TIMER] ✅ Fetch Data from Database: 234.56ms (0.23s)

[PIPELINE-TIMER] ▶️  Brain 4: Image Decision
[PIPELINE-TIMER] ⏳ Brain 4: Image Decision: 1245.78ms (1.25s)

[PIPELINE-TIMER] ▶️  Brain 1: Dialogue Generation
[PIPELINE-TIMER] ⏳ Brain 1: Dialogue Generation: 3456.89ms (3.46s)

[PIPELINE-TIMER] ▶️  Brain 2: State Resolution
[PIPELINE-TIMER] ✅ Brain 2: State Resolution: 1123.45ms (1.12s)

[PIPELINE-TIMER] ▶️  Save to Database
[PIPELINE-TIMER] ✅ Save to Database: 178.90ms (0.18s)

[PIPELINE-TIMER] ▶️  Send Response to User
[PIPELINE-TIMER] ⚡ Send Response to User: 234.12ms (0.23s)

[PIPELINE-TIMER] ▶️  Trigger Background Tasks
[PIPELINE-TIMER] ⚡ Trigger Background Tasks: 12.34ms (0.01s)

================================================================================
[PIPELINE-TIMER] 🏁 SUMMARY: Message Pipeline (Chat: abc-123...)
================================================================================
  • Initialization: 125.43ms (1.9%)
  • Batch #1: Get Messages from Queue: 15.23ms (0.2%)
  • Start Typing Indicator: 45.67ms (0.7%)
  • Fetch Data from Database: 234.56ms (3.5%)
  • Brain 4: Image Decision: 1245.78ms (18.7%)
  • Brain 1: Dialogue Generation: 3456.89ms (51.9%)
  • Brain 2: State Resolution: 1123.45ms (16.9%)
  • Save to Database: 178.90ms (2.7%)
  • Send Response to User: 234.12ms (3.5%)
  • Trigger Background Tasks: 12.34ms (0.2%)
  ────────────────────────────────────────────────────────────────────────────
  TOTAL: 6672.37ms (6.67s)
================================================================================
```

**Смайлики для времени:**
- ⚡ - Быстро (< 1 секунда)
- ✅ - Нормально (1-3 секунды)
- ⏳ - Медленно (> 3 секунды)

### 2. AI Requests (Запросы к AI)

Каждый запрос к AI логируется со всеми деталями:

**Пример вывода:**

```
================================================================================
[DEV-LOG] 🧠 Dialogue Specialist - AI REQUEST
================================================================================
Model: anthropic/claude-3.5-sonnet
Temperature: 0.8
Max Tokens: 512
Additional params: {'top_p': 0.9, 'frequency_penalty': 0.3, 'presence_penalty': 0.3}

📨 MESSAGES (3 total):

  [1] SYSTEM (2345 chars):
  ────────────────────────────────────────────────────────────────────────────
  You are a conversational AI assistant roleplaying as a character.
  Your goal is to provide engaging, natural dialogue responses...
  ... [first 500 chars shown for system prompts]

  [2] USER (67 chars):
  ────────────────────────────────────────────────────────────────────────────
  Hey! What are you up to?

  [3] ASSISTANT (145 chars):
  ────────────────────────────────────────────────────────────────────────────
  *smiles warmly* Just thinking about you actually. How was your day?
================================================================================
```

### 3. AI Responses (Ответы от AI)

Каждый ответ от AI логируется с временем выполнения:

**Пример вывода:**

```
================================================================================
[DEV-LOG] 🎯 Dialogue Specialist - AI RESPONSE
================================================================================
Model: anthropic/claude-3.5-sonnet
Duration: 3456.89ms (3.46s)
Length: 187 chars

📥 RESPONSE:
  ────────────────────────────────────────────────────────────────────────────
  *leans in with a playful smile* Well, since you asked... I was actually 
  thinking about that conversation we had earlier. You always know how to 
  make me curious about what's next! 😊
================================================================================
```

### 4. Все Brain-модули

Детальное логирование для всех AI-модулей:

- **Brain 1: Dialogue Specialist** - Генерация диалогов
- **Brain 2: State Resolver** - Обновление состояния разговора
- **Brain 3: Image Prompt Engineer** - Генерация промптов для изображений
- **Brain 4: Image Decision Specialist** - Решение о генерации изображения

## Структура Логов

### Обычный режим (Production)

```
[PIPELINE] 🚀 ============= STARTING PIPELINE =============
[BATCH] 🧠 Brain 1: Generating dialogue...
[LLM] 🤖 Calling anthropic/claude-3.5-sonnet (temp=0.8, max_tokens=512)
[LLM] ✅ Response received (187 chars) in 3456.89ms
[BATCH] ✅ Brain 1: Dialogue generated (187 chars)
```

### Development режим

Добавляется детальная информация:

```
[PIPELINE] 🚀 ============= STARTING PIPELINE =============

================================================================================
[PIPELINE-TIMER] ⏱️  Starting: Message Pipeline (Chat: abc-123...)
================================================================================

────────────────────────────────────────────────────────────────────────────
  BATCH PROCESSING
────────────────────────────────────────────────────────────────────────────

[BATCH] 🧠 Brain 1: Generating dialogue...

================================================================================
[DEV-LOG] 🧠 Dialogue Specialist - AI REQUEST
================================================================================
[полный запрос с всеми промптами]

[LLM] 🤖 Calling anthropic/claude-3.5-sonnet (temp=0.8, max_tokens=512)
[LLM] ✅ Response received (187 chars) in 3456.89ms

================================================================================
[DEV-LOG] 🎯 Dialogue Specialist - AI RESPONSE
================================================================================
[полный ответ]

[BATCH] ✅ Brain 1: Dialogue generated (187 chars)
```

## Использование в Коде

### PipelineTimer

Используется для замера времени этапов пайплайна:

```python
from app.core.logging_utils import PipelineTimer

# Создать таймер
timer = PipelineTimer("My Pipeline")

# Начать этап
timer.start_stage("Database Query")
# ... выполнить работу ...
timer.end_stage()

# Начать следующий этап
timer.start_stage("AI Processing")
# ... выполнить работу ...
timer.end_stage()

# Вывести итоговую статистику
timer.finish()
```

### Context Manager для Замера Времени

```python
from app.core.logging_utils import timer

async def my_function():
    with timer("My Operation"):
        # ... выполнить работу ...
        pass
    # Автоматически выведет: [DEV-TIMING] ⚡ My Operation: 123.45ms (0.12s)
```

### Логирование AI Запросов

```python
from app.core.logging_utils import log_dev_request, log_dev_response
import time

# Логировать запрос (только в dev mode)
log_dev_request(
    brain_name="My Brain",
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.8,
    max_tokens=512
)

start = time.time()
response = await call_ai(...)
duration_ms = (time.time() - start) * 1000

# Логировать ответ (только в dev mode)
log_dev_response(
    brain_name="My Brain",
    model="gpt-4",
    response=response,
    duration_ms=duration_ms
)
```

### Проверка Development Режима

```python
from app.core.logging_utils import is_development, log_verbose, log_dev_section

# Проверить режим
if is_development():
    print("Development mode active!")

# Логировать только в dev
log_verbose("This only shows in development")

# Добавить заголовок секции
log_dev_section("MY SECTION TITLE")
```

## Анализ Performance

### Узкие места

С помощью `PIPELINE-TIMER` можно легко увидеть, где теряется время:

1. **AI запросы** обычно самые медленные (1-5 секунд)
2. **Database queries** должны быть быстрыми (< 200ms)
3. **Batching и queues** должны быть мгновенными (< 50ms)

### Оптимизация

Если видите медленные этапы:

- **Brain 1 (Dialogue)** > 5 секунд → попробуйте уменьшить `max_tokens` или сменить модель
- **Brain 2 (State)** > 2 секунд → используйте более быструю модель
- **Database** > 500ms → проверьте индексы и queries
- **Send Message** > 500ms → проблемы с Telegram API или сетью

## Примеры Реальных Логов

### Успешный запрос

```
[PIPELINE-TIMER] 🏁 SUMMARY: Message Pipeline (Chat: abc-123...)
  • Initialization: 125ms (2%)
  • Brain 4: Image Decision: 890ms (15%)
  • Brain 1: Dialogue Generation: 2340ms (40%)
  • Brain 2: State Resolution: 1120ms (19%)
  • Save to Database: 180ms (3%)
  • Send Response: 230ms (4%)
  TOTAL: 5885ms (5.89s)
```

### Медленный запрос (требует оптимизации)

```
[PIPELINE-TIMER] 🏁 SUMMARY: Message Pipeline (Chat: abc-123...)
  • Initialization: 125ms (1%)
  • Brain 4: Image Decision: 1890ms (12%)  ⚠️
  • Brain 1: Dialogue Generation: 8340ms (55%)  ⚠️ TOO SLOW!
  • Brain 2: State Resolution: 2120ms (14%)  ⚠️
  • Save to Database: 1180ms (8%)  ⚠️ CHECK QUERIES!
  • Send Response: 230ms (2%)
  TOTAL: 13885ms (13.89s)  ❌ USER WILL NOTICE!
```

## Tips

1. **Не используйте в Production** - логи очень verbose и замедляют систему
2. **Используйте для debugging** - детальные логи помогают найти баги
3. **Следите за временем** - таймеры помогают оптимизировать performance
4. **Анализируйте AI запросы** - смотрите, что отправляется в промптах
5. **Проверяйте ответы AI** - убедитесь, что AI возвращает корректные данные

## Отключение

Просто измените `ENVIRONMENT` обратно на `production`:

```bash
ENVIRONMENT=production
```

Или удалите переменную из `.env` файла.

Все детальные логи автоматически отключатся, останутся только критические сообщения.

