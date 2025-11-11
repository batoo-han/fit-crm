"""Minimal Tinkoff payment creation (Init) wrapper returning confirmation URL.
This is a simplified implementation for demo; production should verify signatures and handle more fields.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import aiohttp
import hashlib
from config import TINKOFF_TERMINAL_KEY, TINKOFF_SECRET_KEY, TINKOFF_RETURN_URL
from loguru import logger


def _tinkoff_token(payload: Dict[str, Any], secret: Optional[str] = None) -> str:
    """Generate token per Tinkoff: sort fields, concat values + secret, and SHA256."""
    sec = secret or TINKOFF_SECRET_KEY
    if not sec:
        return ""
    data = {k: v for k, v in payload.items() if k != "Token" and v is not None}
    keys = sorted(data.keys())
    s = ""
    for k in keys:
        s += str(data[k])
    s += sec
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


async def create_tinkoff_payment(
    amount: float,
    description: str,
    payment_id: str,
    customer_email: Optional[str] = None,
    override_terminal_key: Optional[str] = None,
    override_secret_key: Optional[str] = None,
    override_return_url: Optional[str] = None,
) -> Dict[str, Any]:
    terminal = override_terminal_key or TINKOFF_TERMINAL_KEY
    secret = override_secret_key or TINKOFF_SECRET_KEY
    return_url = override_return_url or TINKOFF_RETURN_URL
    if not (terminal and secret):
        raise RuntimeError("Tinkoff credentials are not configured")

    url = "https://securepay.tinkoff.ru/v2/Init"
    payload: Dict[str, Any] = {
        "TerminalKey": terminal,
        "Amount": int(round(amount * 100)),  # kopecks
        "OrderId": payment_id,
        "Description": description[:250],
        "SuccessURL": return_url,
        "FailURL": return_url,
        "NotificationURL": None,  # can be set to webhook endpoint if implemented
        "Receipt": {
            "Email": customer_email or "client@batoohan.ru",
            "Taxation": "usn_income_outcome",
            "Items": [
                {
                    "Name": description[:100],
                    "Price": int(round(amount * 100)),
                    "Quantity": 1.0,
                    "Amount": int(round(amount * 100)),
                    "Tax": "none",
                    "PaymentMethod": "full_payment",
                    "PaymentObject": "service",
                }
            ],
        },
    }
    payload["Token"] = _tinkoff_token(payload, secret=secret)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=30) as resp:
            data = await resp.json()
            if not resp.ok or not data.get("Success"):
                logger.error(f"Tinkoff Init error: {data}")
                raise RuntimeError(f"Tinkoff error: {data}")
            # Confirmation URL in PaymentURL
            return {
                "id": data.get("PaymentId"),
                "confirmation": {"confirmation_url": data.get("PaymentURL")},
            }


def parse_tinkoff_status(status: str) -> str:
    status = (status or "").lower()
    mapping = {
        "authorized": "pending",
        "confirmed": "completed",
        "rejected": "failed",
        "canceled": "failed",
    }
    return mapping.get(status, "pending")


def verify_tinkoff_token(payload: Dict[str, Any], secret: Optional[str] = None) -> bool:
    provided = (payload.get("Token") or "").lower()
    expected = _tinkoff_token(payload, secret=secret).lower()
    return provided == expected

