"""Catalogue of website services/products available for purchase."""
from __future__ import annotations
from typing import Dict, Any, Optional


SERVICE_CATALOG: Dict[str, Dict[str, Any]] = {
    "online-1-month": {
        "title": "Персональное онлайн-сопровождение (1 месяц)",
        "price": 14999.0,
        "program_type": "paid_monthly",
        "weeks": 4,
        "default_location": "дом",
        "auto_program": True,
        "description": "Полноценная программа трансформации на 4 недели с поддержкой тренера.",
    },
    "online-3-month": {
        "title": "Персональное онлайн-сопровождение (3 месяца)",
        "price": 34999.0,
        "program_type": "paid_3month",
        "weeks": 12,
        "default_location": "дом",
        "auto_program": True,
        "description": "Трёхмесячное сопровождение с прогрессией нагрузок и детальным анализом прогресса.",
    },
    "online-consultation": {
        "title": "Онлайн-консультация (1 час)",
        "price": 1500.0,
        "program_type": "consultation",
        "weeks": 0,
        "default_location": "дом",
        "auto_program": False,
        "description": "Разовый созвон для разбора программы, техники и ответов на вопросы.",
    },
    "offline-10-block": {
        "title": "Блок из 10 оффлайн-тренировок",
        "price": 28900.0,
        "program_type": "paid_offline",
        "weeks": 10,
        "default_location": "зал",
        "auto_program": False,
        "description": "Очный курс тренировок в клубе «С.С.С.Р.» с персональным сопровождением.",
    },
}


def get_service_config(service_id: str) -> Optional[Dict[str, Any]]:
    """Return copy of service configuration for provided identifier."""
    if service_id not in SERVICE_CATALOG:
        return None
    config = SERVICE_CATALOG[service_id].copy()
    config["id"] = service_id
    return config


