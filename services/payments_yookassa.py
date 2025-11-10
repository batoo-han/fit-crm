"""YooKassa payment service integration."""
import aiohttp
import base64
import uuid  # Built-in Python module
from typing import Any, Dict, Optional

from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, YOOKASSA_RETURN_URL


async def create_yookassa_payment(
    amount: float,
    description: str,
    payment_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    customer_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a payment in YooKassa and return its JSON.

    Args:
        amount: Amount in RUB.
        description: Payment description.
        payment_id: Internal payment ID (used in metadata).
        metadata: Optional metadata to attach.

    Returns:
        Dict with YooKassa payment object or raises Exception.
    """
    if not (YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY):
        raise RuntimeError("YooKassa credentials are not configured")

    url = "https://api.yookassa.ru/v3/payments"
    idempotence_key = str(uuid.uuid4())

    auth = base64.b64encode(f"{YOOKASSA_SHOP_ID}:{YOOKASSA_SECRET_KEY}".encode()).decode()

    # Формируем чек согласно 54-ФЗ
    receipt = {
        "customer": {
            "email": customer_email or "client@batoohan.ru"
        },
        "items": [
            {
                "description": description[:128],
                "quantity": "1",
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "vat_code": 1,  # НДС не облагается
                "payment_mode": "full_payment",
                "payment_subject": "service"  # услуга
            }
        ]
    }
    
    payload = {
        "amount": {
            "value": f"{amount:.2f}",
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": YOOKASSA_RETURN_URL,
        },
        "capture": True,
        "description": description[:128],
        "receipt": receipt,
        "metadata": {"payment_id": payment_id, **(metadata or {})},
    }

    headers = {
        "Idempotence-Key": idempotence_key,
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=30) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise RuntimeError(f"YooKassa error {resp.status}: {data}")
            return data


