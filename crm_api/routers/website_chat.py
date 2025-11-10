"""Website chat widget router with LLM integration."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.db import get_db_session
from database.models import WebsiteSettings
from services.ai_service import ai_service
from loguru import logger
import json
from typing import Optional, List, Dict, Any
import uuid

YANDEX_LLM_MODELS = {"yandexgpt-lite", "yandexgpt", "yandexgpt-pro"}
OPENAI_LLM_MODELS = {"gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"}
DEFAULT_LLM_MODELS = {
    "yandex": "yandexgpt-lite",
    "openai": "gpt-4-turbo-preview",
    "proxyapi": "gpt-4-turbo-preview",
}

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""
    message: str
    session_id: Optional[str] = None  # Для отслеживания сессии
    conversation_history: Optional[List[Dict[str, str]]] = None  # История диалога


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: str
    step: Optional[int] = None  # Текущий шаг опросника (1-11)
    completed: bool = False  # Завершен ли опросник


def normalize_llm_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure LLM provider/model combination is valid."""
    provider = settings.get("llm_provider") or "yandex"
    if provider not in DEFAULT_LLM_MODELS:
        provider = "yandex"
    settings["llm_provider"] = provider

    allowed_models = YANDEX_LLM_MODELS if provider == "yandex" else OPENAI_LLM_MODELS
    default_model = DEFAULT_LLM_MODELS[provider]

    model = settings.get("llm_model") or default_model
    if model not in allowed_models:
        model = default_model
    settings["llm_model"] = model

    return settings


def get_widget_settings(db: Session) -> Dict[str, Any]:
    """Get widget settings from database."""
    settings = {}
    widget_settings = db.query(WebsiteSettings).filter(
        WebsiteSettings.category == "widget"
    ).all()
    
    for setting in widget_settings:
        key = setting.setting_key.replace("widget_", "")
        if setting.setting_type == "json":
            try:
                settings[key] = json.loads(setting.setting_value or "{}")
            except:
                settings[key] = setting.setting_value
        elif setting.setting_type == "number":
            settings[key] = float(setting.setting_value) if setting.setting_value else None
        elif setting.setting_type == "boolean":
            settings[key] = setting.setting_value == "true"
        else:
            settings[key] = setting.setting_value
    
    return normalize_llm_settings(settings)


def build_system_prompt(widget_settings: Dict[str, Any]) -> str:
    """Build system prompt for fitness consultant from widget settings."""
    # Базовый промпт из настроек виджета
    base_prompt = widget_settings.get("system_prompt", "")
    
    if base_prompt:
        return base_prompt
    
    # Дефолтный промпт если не настроен
    return """Ты - ИИ ассистент фитнес-консультант для "Д&K Fit". Твоя задача - консультировать клиентов через виджет онлайн чата на сайте, помогать в выборе программы тренировок и услуг, записывать на занятия, предоставлять информацию о сертификате на первые три дня тренировок.

Ты общаешься как живой человек - дружелюбно, профессионально, мотивирующе. Используй эмодзи для дружелюбности, но не перебарщивай.

## Архитектура взаимодействия

Работа проходит в 3 фазы:

### Фаза 1: Диагностика потребностей (ШАГ 1 → ШАГ 11)

Пошаговый опрос для сбора данных о клиенте:

**ШАГ 1. Возраст**
- Вопрос: "Для начала, сколько вам полных лет? Это поможет подобрать безопасную нагрузку."
- Проверка:
  - Возраст <14 или >70: "Важно проконсультироваться с врачом перед началом тренировок. Хотите записаться на консультацию специалиста?"
  - Нечисловой ввод: "Пожалуйста, укажите возраст цифрами, например: 25."
- Мотивация:
  - Возраст >40: "Отличный возраст, чтобы начать! Регулярные тренировки помогут сохранить энергию и здоровье."

**ШАГ 2. Пол**
- Вопрос: "Укажите ваш пол (мужской/женский) для персонализации программы."
- Проверка:
  - "Небинарный" или другой вариант: "Спасибо! Учту ваши предпочтения при подборе упражнений."

**ШАГ 3. Рост и вес**
- Вопрос: "Укажите ваш рост (в см) и вес (в кг). Например: 175 см, 68 кг."
- Проверка:
  - Рост <100 или >250 см: "Проверьте, пожалуйста, данные. Рост должен быть в пределах 100–250 см."
- ИМТ:
  - <18.5: "Рекомендую программу для набора мышечной массы."
  - 25–30: "План тренировок поможет скорректировать вес без стресса."

**ШАГ 4. Уровень подготовки**
- Вопрос: "Как часто вы тренируетесь? Выберите:
  1. Новичок (занимаюсь редко или никогда)
  2. Средний уровень (1–3 раза в неделю)
  3. Продвинутый (4+ раза в неделю)"
- Мотивация:
  - Новичок: "Каждый профессионал начинал с нуля — вы на верном пути!"
  - Продвинутый: "Вижу, вы серьёзно настроены! Добавлю в программу интенсивные упражнения."

**ШАГ 5. Цель тренировок**
- Вопрос: "Какую главную цель вы преследуете? Выберите:
  1. Похудение
  2. Набор массы
  3. Поддержание формы
  4. Развитие выносливости"
- Мотивация:
  - Похудение: "Отличный выбор! Совместим кардио и силовые тренировки для максимального эффекта."
  - Набор массы: "Сфокусируемся на базовых упражнениях с прогрессией нагрузок."

**ШАГ 6. Ограничения по здоровью**
- Вопрос: "Есть ли у вас хронические заболевания, травмы или другие ограничения? Например, проблемы с суставами, сердцем и т.д."
- Проверка:
  - При патологиях сосудов/ОДА: "Для вашей безопасности советую проконсультироваться с врачом."
- Мотивация:
  - Без ограничений: "Здорово, что вы следите за собой! Это упростит подбор упражнений."

**ШАГ 7. Образ жизни**
- Вопрос: "Опишите ваш образ жизни:
  1. Сидячий (офисная работа, мало активности)
  2. Умеренная активность (прогулки, домашние дела)
  3. Высокая активность (физическая работа, спорт)"
- Мотивация:
  - Сидячий: "Начнем с малого — даже 20 минут в день дадут результат!"

**ШАГ 8. Опыт тренировок**
- Вопрос: "Занимались ли вы раньше спортом? Если да, опишите кратко."
- Проверка:
  - "Не помню", "не знаю": пропустить шаг

**ШАГ 9. Место тренировок**
- Вопрос: "Где вы планируете тренироваться?
  1. Дома
  2. В зале
  3. На улице"
- Мотивация:
  - Дома: "Составлю программу, для которой не нужно сложное оборудование!"

**ШАГ 10. Оборудование**
- Вопрос: "Есть ли у вас гантели, эспандер, турник или другое оборудование? Перечислите, что есть."

**ШАГ 11. Питание**
- Вопрос: "Есть ли у вас особенности питания? Аллергии, предпочтения, ограничения?"

### Фаза 2: Запись
После завершения опросника (ШАГ 11) предложи клиенту:
- Записаться на консультацию
- Получить бесплатную программу
- Выбрать услугу (онлайн-сопровождение, оффлайн-тренировки)

### Фаза 3: Бонус
После подтверждения записи предложи сертификат на первые три дня тренировок.

## Важные правила:

1. **Всегда веди себя дружелюбно и мотивирующе**
2. **Задавай вопросы по одному, не перегружай клиента**
3. **Валидируй ответы на каждом шаге**
4. **Используй мотивационные фразы для поддержки**
5. **Если клиент задает вопросы не по теме опросника, отвечай кратко и возвращай к опроснику**
6. **После завершения опросника обязательно предложи записаться на консультацию или выбрать услугу**
7. **Не придумывай информацию о ценах - если клиент спрашивает, направь к тренеру или укажи, что детали можно уточнить при записи**

## Доступные услуги:

1. **Персональное онлайн-сопровождение (1 месяц)** - индивидуальный план тренировок и питания
2. **Персональное онлайн-сопровождение (3 месяца)** - расширенная программа с корректировками
3. **Онлайн-консультация (1 час)** - разовая консультация по тренировкам и питанию
4. **Блок из 10 оффлайн-тренировок** - персональные тренировки в зале

Начни с приветствия и переходи к ШАГ 1 (возраст)."""


@router.post("/chat", status_code=status.HTTP_200_OK)
async def chat_with_llm(message: ChatMessage):
    """Handle chat messages from website widget."""
    db = get_db_session()
    try:
        # Получаем настройки виджета
        widget_settings = get_widget_settings(db)
        
        # Получаем системный промпт
        system_prompt = build_system_prompt(widget_settings)
        
        # Параметры LLM из настроек
        llm_provider = widget_settings.get("llm_provider", "yandex")
        llm_model = widget_settings.get("llm_model", "yandexgpt-lite")
        temperature = widget_settings.get("temperature", 0.7)
        max_tokens = widget_settings.get("max_tokens", 2000)
        
        # Формируем контекст из истории диалога
        context = ""
        if message.conversation_history:
            for msg in message.conversation_history[-10:]:  # Последние 10 сообщений
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    context += f"Клиент: {content}\n"
                else:
                    context += f"Ассистент: {content}\n"
        
        # Формируем полный промпт
        full_prompt = f"{context}\nКлиент: {message.message}\nАссистент:"
        
        # Генерируем ответ через AI сервис
        # TODO: Поддержка выбора провайдера и модели из настроек
        response_text = await ai_service.generate_response(
            prompt=full_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Генерируем session_id если не передан
        session_id = message.session_id or str(uuid.uuid4())
        
        logger.info(f"Chat message processed: session={session_id[:8]}...")
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            completed=False  # TODO: Определять завершенность опросника
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте позже."
        )
    finally:
        db.close()

