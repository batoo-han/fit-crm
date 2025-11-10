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
    name = Column(String(100), nullable=False)  # Название этапа
    order = Column(Integer, nullable=False, default=0)  # Порядок в воронке
    color = Column(String(20), default="#3B82F6")  # Цвет для UI (hex)
    description = Column(Text, nullable=True)  # Описание этапа
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client_pipelines = relationship("ClientPipeline", back_populates="stage")


class ClientPipeline(Base):
    """Client pipeline tracking - tracks client movement through sales funnel."""
    __tablename__ = "client_pipelines"

    id = Column(Integer, primary_key=True)
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


# Обновим существующие модели (добавим relationships)
# Это будет сделано через миграции и обновление models.py

