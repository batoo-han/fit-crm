# AI Service - Сервис для работы с AI моделями

## Описание

Сервис для работы с AI моделями Yandex GPT и OpenAI с автоматическим fallback между провайдерами.

## Поддерживаемые провайдеры

1. **Yandex GPT** (приоритет 1)
   - Модели: `yandexgpt-lite`, `yandexgpt`, `yandexgpt-pro`
   - Российский сервис
   - Быстрый и недорогой

2. **OpenAI через ProxyAPI** (fallback)
   - Для обхода блокировок
   - Proxy: https://api.proxyapi.ru

3. **OpenAI напрямую** (fallback)
   - Прямое подключение к OpenAI API

## Настройка

### В файле .env

```env
# Yandex GPT
YANDEX_API_KEY=your_key
YANDEX_FOLDER_ID=your_folder_id
YANDEX_GPT_MODEL=yandexgpt-lite

# OpenAI
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4-turbo-preview

# ProxyAPI (опционально)
PROXYAPI_BASE_URL=https://api.proxyapi.ru/openai/v1
PROXYAPI_API_KEY=your_key
```

## Использование

### Базовое использование

```python
from services.ai_service import ai_service

# Простой запрос
response = await ai_service.generate_response("Привет!")
print(response)
```

### С системным промптом

```python
system_prompt = "Ты - фитнес-тренер. Отвечай кратко и по делу."

user_prompt = "Сколько подходов делать для набора массы?"

response = await ai_service.generate_response(
    prompt=user_prompt,
    system_prompt=system_prompt,
    max_tokens=500,
    temperature=0.7
)
```

### Пример в обработчике бота

```python
from aiogram import Router
from aiogram.types import Message
from services.ai_service import ai_service

router = Router()

@router.message(F.text)
async def handle_message(message: Message):
    user_question = message.text
    
    # Генерируем ответ через AI
    try:
        ai_response = await ai_service.generate_response(
            prompt=user_question,
            system_prompt="Ты - фитнес-тренер Данила. Отвечай профессионально.",
            max_tokens=1000
        )
        await message.answer(ai_response)
    except Exception as e:
        await message.answer("Извините, не могу обработать запрос. Обратитесь к тренеру.")
```

## Параметры

### `generate_response()`

- **prompt** (str, required) - Текст запроса от пользователя
- **system_prompt** (str, optional) - Системный промпт для настройки поведения AI
- **max_tokens** (int, default=2000) - Максимальная длина ответа
- **temperature** (float, default=0.7) - Креативность ответа (0.0-1.0)

### Temperature

- **0.0-0.3**: Детерминированные, фактические ответы
- **0.4-0.7**: Сбалансированные ответы (рекомендуется)
- **0.8-1.0**: Креативные, разнообразные ответы

## Логика fallback

Сервис автоматически переключается между провайдерами:

```
1. Пробует Yandex GPT
   ↓ (ошибка)
2. Пробует OpenAI через ProxyAPI
   ↓ (ошибка)
3. Пробует OpenAI напрямую
   ↓ (ошибка)
4. Возвращает ошибку
```

## Примеры использования

### FAQ бот

```python
@router.message(F.text)
async def faq_handler(message: Message):
    # Проверяем, есть ли ответ в базе
    faq_answer = check_faq_database(message.text)
    
    if faq_answer:
        await message.answer(faq_answer)
    else:
        # Используем AI для генерации ответа
        ai_response = await ai_service.generate_response(
            prompt=f"Ответь на вопрос о фитнесе: {message.text}",
            system_prompt="Ты - профессиональный фитнес-тренер.",
            max_tokens=300
        )
        await message.answer(ai_response)
```

### Генерация программ тренировок

```python
async def generate_workout_program(client_data):
    prompt = f"""
    Создай программу тренировок для:
    - Пол: {client_data['gender']}
    - Возраст: {client_data['age']}
    - Опыт: {client_data['experience']}
    - Цель: {client_data['goal']}
    """
    
    program = await ai_service.generate_response(
        prompt=prompt,
        system_prompt="Ты - эксперт по программированию тренировок. Создавай безопасные программы.",
        max_tokens=2000,
        temperature=0.5
    )
    
    return program
```

### Нутрициология

```python
async def generate_nutrition_plan(client_data):
    prompt = f"""
    Создай план питания для:
    - Вес: {client_data['weight']} кг
    - Рост: {client_data['height']} см
    - Цель: {client_data['goal']}
    """
    
    nutrition = await ai_service.generate_response(
        prompt=prompt,
        system_prompt="Ты - нутрициолог. Составляй сбалансированные планы питания.",
        max_tokens=1500,
        temperature=0.4
    )
    
    return nutrition
```

## Обработка ошибок

```python
try:
    response = await ai_service.generate_response(prompt)
except Exception as e:
    logger.error(f"AI service error: {e}")
    # Отправить уведомление администратору
    # Вернуть пользователю стандартный ответ
```

## Рекомендации

1. **Начните с yandexgpt-lite** - быстрый и недорогой
2. **Используйте system_prompt** - улучшает качество ответов
3. **Ограничьте max_tokens** - для экономии средств
4. **Добавьте обработку ошибок** - для лучшего UX
5. **Логируйте запросы** - для аналитики и отладки

## Отладка

Проверка текущего провайдера:

```python
print(ai_service.preferred_provider)  # yandex, proxyapi, openai или none
```

Проверка доступности сервиса:

```python
try:
    response = await ai_service.generate_response("Тест")
    print("AI сервис работает!")
except:
    print("r Ошибка AI сервиса")
```
