from __future__ import annotations
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger
import requests
import time
import json
from config import AMOCRM_DOMAIN, AMOCRM_CLIENT_ID, AMOCRM_CLIENT_SECRET, AMOCRM_REDIRECT_URI
from database.models import Client
from database.models import WebsiteSettings


SETTINGS_KEYS = {
    "enabled": "amocrm.enabled",
    "tokens": "amocrm.tokens",
    "domain": "amocrm.domain",
    "client_id": "amocrm.client_id",
    "client_secret": "amocrm.client_secret",
    "redirect_uri": "amocrm.redirect_uri",
    "mode": "crm.mode",  # internal | amocrm
}


def _get_setting(db: Session, key: str) -> Optional[str]:
    row = db.query(WebsiteSettings).filter(WebsiteSettings.setting_key == key).first()
    return row.setting_value if row else None


def _set_setting(db: Session, key: str, value: Any, setting_type: str = "string", category: str = "integrations") -> None:
    row = db.query(WebsiteSettings).filter(WebsiteSettings.setting_key == key).first()
    if not row:
        row = WebsiteSettings(setting_key=key, setting_type=setting_type, category=category)
        db.add(row)
    row.setting_value = json.dumps(value, ensure_ascii=False) if setting_type == "json" else str(value)
    db.commit()


class AmoCrmService:
    @staticmethod
    def is_enabled(db: Session) -> bool:
        val = _get_setting(db, SETTINGS_KEYS["enabled"])
        if val is None:
            return False
        try:
            return json.loads(val) if val in ("true", "false") else (val.lower() in ("1", "true", "yes"))
        except Exception:
            return val.lower() in ("1", "true", "yes")

    @staticmethod
    def set_enabled(db: Session, enabled: bool) -> None:
        _set_setting(db, SETTINGS_KEYS["enabled"], enabled, setting_type="string")
        _set_setting(db, SETTINGS_KEYS["mode"], "amocrm" if enabled else "internal", setting_type="string")

    @staticmethod
    def save_credentials(db: Session, domain: str, client_id: str, client_secret: str, redirect_uri: str) -> None:
        _set_setting(db, SETTINGS_KEYS["domain"], domain, "string")
        _set_setting(db, SETTINGS_KEYS["client_id"], client_id, "string")
        _set_setting(db, SETTINGS_KEYS["client_secret"], client_secret, "string")
        _set_setting(db, SETTINGS_KEYS["redirect_uri"], redirect_uri, "string")

    @staticmethod
    def get_credentials(db: Session) -> Dict[str, str]:
        return {
            "domain": _get_setting(db, SETTINGS_KEYS["domain"]) or AMOCRM_DOMAIN or "",
            "client_id": _get_setting(db, SETTINGS_KEYS["client_id"]) or AMOCRM_CLIENT_ID or "",
            "client_secret": _get_setting(db, SETTINGS_KEYS["client_secret"]) or AMOCRM_CLIENT_SECRET or "",
            "redirect_uri": _get_setting(db, SETTINGS_KEYS["redirect_uri"]) or AMOCRM_REDIRECT_URI or "",
        }

    @staticmethod
    def save_tokens(db: Session, tokens: Dict[str, Any]) -> None:
        # augment with expires_at
        expires_in = tokens.get("expires_in", 0)
        tokens["expires_at"] = int(time.time()) + int(expires_in)
        _set_setting(db, SETTINGS_KEYS["tokens"], tokens, setting_type="json")

    @staticmethod
    def get_tokens(db: Session) -> Optional[Dict[str, Any]]:
        raw = _get_setting(db, SETTINGS_KEYS["tokens"])
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    @staticmethod
    def exchange_code_for_tokens(db: Session, auth_code: str) -> Dict[str, Any]:
        creds = AmoCrmService.get_credentials(db)
        url = f"https://{creds['domain']}/oauth2/access_token"
        payload = {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": creds["redirect_uri"],
        }
        resp = requests.post(url, json=payload, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"amoCRM token exchange failed: {resp.text}")
        data = resp.json()
        AmoCrmService.save_tokens(db, data)
        return data

    @staticmethod
    def ensure_access_token(db: Session) -> str:
        tokens = AmoCrmService.get_tokens(db)
        if not tokens:
            raise RuntimeError("amoCRM tokens not set")
        if int(time.time()) < int(tokens.get("expires_at", 0)) - 60:
            return tokens.get("access_token", "")
        # refresh
        creds = AmoCrmService.get_credentials(db)
        url = f"https://{creds['domain']}/oauth2/access_token"
        payload = {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": tokens.get("refresh_token"),
            "redirect_uri": creds["redirect_uri"],
        }
        resp = requests.post(url, json=payload, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"amoCRM token refresh failed: {resp.text}")
        data = resp.json()
        AmoCrmService.save_tokens(db, data)
        return data.get("access_token", "")

    @staticmethod
    def upsert_contact(db: Session, client: Client) -> Optional[int]:
        if not AmoCrmService.is_enabled(db):
            return None
        creds = AmoCrmService.get_credentials(db)
        token = AmoCrmService.ensure_access_token(db)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        # Try find by phone/email not implemented; create/update simple contact
        contact = {
            "name": f"{client.first_name or ''} {client.last_name or ''}".strip() or f"Client {client.id}",
            "custom_fields_values": [],
        }
        if client.phone_number:
            contact["custom_fields_values"].append({
                "field_code": "PHONE",
                "values": [{"value": client.phone_number}]
            })
        if client.telegram_username:
            contact["custom_fields_values"].append({
                "field_name": "Telegram",
                "values": [{"value": f"@{client.telegram_username}"}]
            })
        url = f"https://{creds['domain']}/api/v4/contacts"
        resp = requests.post(url, headers=headers, json=[contact], timeout=30)
        if not resp.ok:
            logger.error(f"amoCRM upsert contact failed: {resp.text}")
            return None
        data = resp.json()
        try:
            return int(data["_embedded"]["contacts"][0]["id"])
        except Exception:
            return None


