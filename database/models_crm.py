"""CRM-specific database models for fitness trainer system."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database.models import Base


class PipelineStage(Base):
    """Pipeline stage model - stages in sales funnel."""
    __tablename__ = "pipeline_stages"

    id = Column(Integer, primary_key=True)
    pipeline_id = Column(Integer, ForeignKey("sales_pipelines.id"), nullable=True)  # принадлежность воронке (nullable = Default)
    name = Column(String(100), nullable=False)  # Название этапа
    order = Column(Integer, nullable=False, default=0)  # Порядок в воронке
    color = Column(String(20), default="#3B82F6")  # Цвет для UI (hex)
    description = Column(Text, nullable=True)  # Описание этапа
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client_pipelines = relationship("ClientPipeline", back_populates="stage")
    pipeline = relationship("SalesPipeline", back_populates="stages")


class ClientPipeline(Base):
    """Client pipeline tracking - tracks client movement through sales funnel."""
    __tablename__ = "client_pipelines"

    id = Column(Integer, primary_key=True)
    pipeline_id = Column(Integer, ForeignKey("sales_pipelines.id"), nullable=True)  # какая воронка
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("pipeline_stages.id"), nullable=False)
    moved_at = Column(DateTime, default=datetime.utcnow)
    moved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who moved client
    notes = Column(Text, nullable=True)  # Примечания при перемещении
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="pipeline_history", foreign_keys="[ClientPipeline.client_id]")
    stage = relationship("PipelineStage", back_populates="client_pipelines")
    moved_by_user = relationship("User", foreign_keys="[ClientPipeline.moved_by]")
    pipeline = relationship("SalesPipeline", back_populates="client_entries")


class ClientBotLink(Base):
    """Mapping tokens to clients for Telegram deep links."""
    __tablename__ = "client_bot_links"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    invite_token = Column(String(64), unique=True, nullable=False, index=True)
    source = Column(String(50), nullable=True, default="website_contact")
    # Контекст для персонального приветствия (JSON string with service, message, etc.)
    context_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    used_at = Column(DateTime, nullable=True)
    used_by_telegram_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    client = relationship("Client", back_populates="bot_links", foreign_keys="[ClientBotLink.client_id]")


class ActionType(enum.Enum):
    """Types of actions with clients."""
    CALL = "call"
    MESSAGE = "message"
    MEETING = "meeting"
    EMAIL = "email"
    CONSULTATION = "consultation"
    CONSULTATION_SCHEDULED = "consultation_scheduled"
    PROPOSAL_SENT = "proposal_sent"
    FOLLOW_UP = "follow_up"
    PROGRAM_ASSIGNED = "program_assigned"
    PAYMENT_RECEIVED = "payment_received"
    OTHER = "other"


class ClientAction(Base):
    """Client action model - tracks all actions/interactions with clients."""
    __tablename__ = "client_actions"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # ActionType enum as string
    action_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="actions", foreign_keys="[ClientAction.client_id]")
    creator = relationship("User", foreign_keys="[ClientAction.created_by]")


class ContactType(enum.Enum):
    """Types of contact channels."""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    PHONE = "phone"
    OTHER = "other"


class ContactDirection(enum.Enum):
    """Direction of contact."""
    INBOUND = "inbound"  # От клиента
    OUTBOUND = "outbound"  # К клиенту


class ClientContact(Base):
    """Client contact model - stores communication history with clients."""
    __tablename__ = "client_contacts"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    contact_type = Column(String(50), nullable=False)  # ContactType enum as string
    contact_data = Column(String(255), nullable=True)  # Phone, username, email
    message_text = Column(Text, nullable=True)
    direction = Column(String(20), nullable=False)  # ContactDirection enum as string
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="contacts", foreign_keys="[ClientContact.client_id]")


class ProgressPeriod(enum.Enum):
    """Progress measurement periods."""
    BEFORE = "before"  # До начала программы
    WEEK_1 = "week_1"
    WEEK_2 = "week_2"
    WEEK_3 = "week_3"
    WEEK_4 = "week_4"
    WEEK_5 = "week_5"
    WEEK_6 = "week_6"
    WEEK_7 = "week_7"
    WEEK_8 = "week_8"
    WEEK_9 = "week_9"
    WEEK_10 = "week_10"
    WEEK_11 = "week_11"
    WEEK_12 = "week_12"
    AFTER = "after"  # После завершения программы


class ProgressJournal(Base):
    """Progress journal model - tracks client body measurements over time."""
    __tablename__ = "progress_journals"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("training_programs.id"), nullable=True)
    measurement_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    period = Column(String(20), nullable=False)  # ProgressPeriod enum as string
    
    # Body measurements (в см)
    weight = Column(Float, nullable=True)  # Вес (кг)
    chest = Column(Float, nullable=True)  # Грудь
    waist = Column(Float, nullable=True)  # Талия
    lower_abdomen = Column(Float, nullable=True)  # Низ живота
    glutes = Column(Float, nullable=True)  # Ягодицы
    right_thigh = Column(Float, nullable=True)  # Правое бедро
    left_thigh = Column(Float, nullable=True)  # Левое бедро
    right_calf = Column(Float, nullable=True)  # Правая голень
    left_calf = Column(Float, nullable=True)  # Левая голень
    right_arm = Column(Float, nullable=True)  # Правая рука
    left_arm = Column(Float, nullable=True)  # Левая рука
    
    notes = Column(Text, nullable=True)  # Дополнительные заметки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="progress_entries", foreign_keys="[ProgressJournal.client_id]")
    program = relationship("TrainingProgram", back_populates="progress_entries", foreign_keys="[ProgressJournal.program_id]")


class User(Base):
    """User model - CRM users (trainers/admins)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="trainer")  # admin, trainer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client_actions = relationship("ClientAction", back_populates="creator", foreign_keys="[ClientAction.created_by]")
    pipeline_moves = relationship("ClientPipeline", back_populates="moved_by_user", foreign_keys="[ClientPipeline.moved_by]")


class ReminderType(enum.Enum):
    """Types of reminders."""
    FREE_PROGRAM_DAY_3 = "free_program_day_3"  # Напоминание через 3 дня после выдачи бесплатной программы
    FREE_PROGRAM_DAY_5 = "free_program_day_5"  # Напоминание через 5 дней
    FREE_PROGRAM_DAY_7 = "free_program_day_7"  # Напоминание через 7 дней (предложение оплаты)
    PAYMENT_REMINDER = "payment_reminder"  # Напоминание об оплате
    FOLLOW_UP = "follow_up"  # Напоминание о следующем контакте


class Reminder(Base):
    """Reminder model - tracks automated reminders for clients."""
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    program_id = Column(Integer, ForeignKey("training_programs.id"), nullable=True)
    reminder_type = Column(String(50), nullable=False)  # ReminderType enum as string
    scheduled_at = Column(DateTime, nullable=False)  # Когда должно быть отправлено
    sent_at = Column(DateTime, nullable=True)  # Когда было отправлено
    is_sent = Column(Boolean, default=False)  # Отправлено ли напоминание
    message_text = Column(Text, nullable=True)  # Текст напоминания
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="reminders", foreign_keys="[Reminder.client_id]")
    program = relationship("TrainingProgram", foreign_keys="[Reminder.program_id]")


class FAQ(Base):
    """FAQ model - stores frequently asked questions and answers."""
    __tablename__ = "faq"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)  # Вопрос
    answer = Column(Text, nullable=False)  # Ответ
    category = Column(String(50), nullable=True)  # Категория (pricing, training, health, etc.)
    keywords = Column(Text, nullable=True)  # Ключевые слова для поиска (JSON array)
    priority = Column(Integer, default=0)  # Приоритет (чем выше, тем чаще показывается)
    is_active = Column(Boolean, default=True)  # Активен ли вопрос
    use_count = Column(Integer, default=0)  # Сколько раз использовался
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто создал
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто обновил

    creator = relationship("User", foreign_keys="[FAQ.created_by]")
    updater = relationship("User", foreign_keys="[FAQ.updated_by]")


class SalesScenario(Base):
    """Sales scenario model - stores sales scenarios with triggers and messages."""
    __tablename__ = "sales_scenarios"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # Название сценария
    description = Column(Text, nullable=True)  # Описание сценария
    trigger_type = Column(String(50), nullable=False)  # Тип триггера (client_action, pipeline_stage, time_based, etc.)
    trigger_conditions = Column(Text, nullable=True)  # Условия триггера (JSON)
    message_template = Column(Text, nullable=False)  # Шаблон сообщения
    action_type = Column(String(50), nullable=True)  # Тип действия (suggest_program, suggest_consultation, etc.)
    is_active = Column(Boolean, default=True)  # Активен ли сценарий
    priority = Column(Integer, default=0)  # Приоритет
    use_count = Column(Integer, default=0)  # Сколько раз использовался
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    creator = relationship("User", foreign_keys="[SalesScenario.created_by]")
    updater = relationship("User", foreign_keys="[SalesScenario.updated_by]")

class MarketingChannel(enum.Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    BOTH = "both"

class CampaignStatus(enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"

class MarketingCampaign(Base):
    """Marketing campaign definition."""
    __tablename__ = "marketing_campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=CampaignStatus.DRAFT.value)
    channel = Column(String(20), default=MarketingChannel.BOTH.value)
    schedule_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    params = Column(Text, nullable=True)  # JSON: throttling, UTM, etc.

class CampaignAudience(Base):
    """Segment definition used by campaigns."""
    __tablename__ = "campaign_audiences"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    filter_json = Column(Text, nullable=True)  # JSON DSL for selecting clients
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class CampaignMessage(Base):
    """Multi-channel message template for campaigns."""
    __tablename__ = "campaign_messages"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    body_text = Column(Text, nullable=False)  # Text template, variables via {first_name}, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CampaignRun(Base):
    """Execution instance for a campaign (each schedule creates run)."""
    __tablename__ = "campaign_runs"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=False, index=True)
    audience_id = Column(Integer, ForeignKey("campaign_audiences.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")  # pending, running, completed, failed, paused
    total = Column(Integer, default=0)
    sent = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    meta = Column(Text, nullable=True)  # JSON metrics, logs brief

class ClientChannelPreference(Base):
    """Client-level channel preferences for marketing."""
    __tablename__ = "client_channel_preferences"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    allow_telegram = Column(Boolean, default=True)
    allow_email = Column(Boolean, default=True)
    quiet_hours_start = Column(Integer, nullable=True)  # 0-23
    quiet_hours_end = Column(Integer, nullable=True)    # 0-23
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CampaignDelivery(Base):
    """Per-client delivery log to enforce deduplication and frequency limits."""
    __tablename__ = "campaign_deliveries"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("campaign_runs.id"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("marketing_campaigns.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)  # telegram/email
    status = Column(String(20), default="sent")  # sent/failed/skipped
    created_at = Column(DateTime, default=datetime.utcnow)

class SocialPost(Base):
    """Scheduled social network posts."""
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True)
    platform = Column(String(30), nullable=False, default="telegram")  # telegram | vk | instagram
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    media_url = Column(String(500), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="draft")  # draft | scheduled | sent | failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SocialPostTemplate(Base):
    """Reusable templates for social posts."""
    __tablename__ = "social_post_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, unique=True)
    platform = Column(String(30), nullable=True)  # optional default platform
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    media_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PromoCode(Base):
    """Promo codes for discounts."""
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    discount_type = Column(String(20), default="percent")  # percent | fixed
    discount_value = Column(Float, nullable=False, default=0)
    max_usage = Column(Integer, nullable=True)
    per_client_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PromoUsage(Base):
    """Tracks promo code usage per client."""
    __tablename__ = "promo_code_usages"

    id = Column(Integer, primary_key=True)
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    used_at = Column(DateTime, default=datetime.utcnow)


class SalesPipeline(Base):
    """Multiple named sales funnels with parameters and enable/disable."""
    __tablename__ = "sales_pipelines"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    # JSON as text for simple storage of parameters/conditions (visibility rules, target segments, etc.)
    params = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    stages = relationship("PipelineStage", back_populates="pipeline")
    client_entries = relationship("ClientPipeline", back_populates="pipeline")

# Обновим существующие модели (добавим relationships)
# Это будет сделано через миграции и обновление models.py

