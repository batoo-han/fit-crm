"""Database models for the fitness trainer bot."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Client(Base):
    """Client model - stores information about users."""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    gender = Column(String(20), nullable=True)  # мужской, женский
    age = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)  # в см
    weight = Column(Float, nullable=True)  # в кг
    bmi = Column(Float, nullable=True)  # индекс массы тела
    experience_level = Column(String(50), nullable=True)  # новичок, средний, продвинутый
    fitness_goals = Column(Text, nullable=True)  # похудение, набор массы, поддержание формы, выносливость
    health_restrictions = Column(Text, nullable=True)  # ограничения по здоровью
    lifestyle = Column(String(50), nullable=True)  # сидячий, умеренная активность, высокая активность
    training_history = Column(Text, nullable=True)  # история тренировок
    location = Column(String(50), nullable=True)  # дом, зал, улица
    equipment = Column(Text, nullable=True)  # оборудование
    nutrition = Column(Text, nullable=True)  # особенности питания
    current_program_id = Column(Integer, nullable=True)
    status = Column(String(50), default="new")  # new, qualified, client, inactive
    pipeline_stage_id = Column(Integer, ForeignKey("pipeline_stages.id"), nullable=True)  # Текущий этап воронки
    last_contact_at = Column(DateTime, nullable=True)  # Последний контакт
    next_contact_at = Column(DateTime, nullable=True)  # Следующий запланированный контакт
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    programs = relationship("TrainingProgram", back_populates="client", foreign_keys="[TrainingProgram.client_id]")
    payments = relationship("Payment", back_populates="client")
    # CRM relationships (will be added when models_crm is imported)
    pipeline_history = relationship("ClientPipeline", back_populates="client", foreign_keys="[ClientPipeline.client_id]")
    actions = relationship("ClientAction", back_populates="client", foreign_keys="[ClientAction.client_id]")
    contacts = relationship("ClientContact", back_populates="client", foreign_keys="[ClientContact.client_id]")
    progress_entries = relationship("ProgressJournal", back_populates="client", foreign_keys="[ProgressJournal.client_id]")


class TrainingProgram(Base):
    """Training program model - stores generated training programs."""
    __tablename__ = "training_programs"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    program_type = Column(String(50))  # free_demo, paid_monthly, paid_3month
    program_data = Column(Text)  # JSON string with program details
    formatted_program = Column(Text, nullable=True)  # Отформатированный текст программы для просмотра
    is_completed = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=False)  # Оплачена ли программа
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто назначил программу
    assigned_at = Column(DateTime, nullable=True)  # Когда назначена
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="programs")
    progress_entries = relationship("ProgressJournal", back_populates="program", foreign_keys="[ProgressJournal.program_id]")


class Payment(Base):
    """Payment model - stores payment transactions."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="RUB")
    payment_type = Column(String(50))  # consultation, 1_month, 3_months
    status = Column(String(50), default="pending")  # pending, completed, failed
    payment_method = Column(String(50))  # tinkoff, manual
    payment_id = Column(String(255), nullable=True)  # External payment ID
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="payments")


class Lead(Base):
    """Lead model - stores information about potential clients."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    source = Column(String(50))  # telegram, website, social
    qualification_data = Column(Text)  # JSON string with questionnaire answers
    status = Column(String(50), default="new")  # new, contacted, qualified, client, lost
    converted_to_client = Column(Boolean, default=False)
    client_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebsiteContact(Base):
    """Website contact form submissions."""
    __tablename__ = "website_contacts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    service = Column(String(100), nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)  # 0 - новая, 1 - обработана


class WebsiteSettings(Base):
    """Website settings and configuration."""
    __tablename__ = "website_settings"
    
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=True)  # JSON string for complex settings
    setting_type = Column(String(50), default="string")  # string, json, number, boolean
    category = Column(String(50), nullable=True)  # general, header, footer, colors, fonts, widget, etc.
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)