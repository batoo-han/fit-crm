"""Utility functions for delivering programs to clients via Telegram/E-mail."""
from __future__ import annotations

import os
import requests
import smtplib
from email.message import EmailMessage
from typing import List, Optional, Dict, Any

from loguru import logger

from config import TELEGRAM_BOT_TOKEN
from database.models import TrainingProgram, Client
from services.pdf_generator import PDFGenerator


def deliver_program_to_client(
    program: TrainingProgram,
    client: Client,
    channels: List[str],
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deliver program file to client via selected channels.

    Args:
        program: TrainingProgram instance with formatted_program.
        client: Client instance (expects telegram_id/email).
        channels: Channels list, e.g. ["telegram","email"].
        message: Optional message text.

    Returns:
        Dict with delivery results per channel.
    """
    results: Dict[str, Any] = {}

    if not program.formatted_program:
        logger.warning("Program has no formatted text, cannot deliver")
        return {"error": "Program has no formatted text"}

    pdf_path = PDFGenerator.generate_program_pdf(
        program_text=program.formatted_program,
        client_id=program.client_id,
        client_name=client.first_name or "Клиент",
    )
    if not pdf_path or not os.path.exists(pdf_path):
        logger.error("Failed to generate PDF for program delivery")
        return {"error": "Failed to generate PDF"}

    if "telegram" in channels:
        if not TELEGRAM_BOT_TOKEN or not client.telegram_id:
            results["telegram"] = {"success": False, "error": "Нет Telegram токена или chat_id клиента"}
        else:
            try:
                with open(pdf_path, "rb") as pdf_file:
                    files = {"document": (os.path.basename(pdf_path), pdf_file)}
                    data = {
                        "chat_id": client.telegram_id,
                        "caption": message or "Ваша персональная программа тренировок",
                        "disable_notification": False,
                    }
                    resp = requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                        data=data,
                        files=files,
                        timeout=20,
                    )
                if resp.ok:
                    results["telegram"] = {"success": True}
                else:
                    results["telegram"] = {"success": False, "error": resp.text}
            except Exception as exc:
                logger.error(f"Telegram delivery error: {exc}")
                results["telegram"] = {"success": False, "error": str(exc)}

    if "email" in channels:
        recipient = getattr(client, "email", None)
        if not recipient or "@" not in recipient:
            results["email"] = {"success": False, "error": "У клиента не указан e-mail"}
        else:
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            smtp_from = os.getenv("SMTP_FROM", smtp_user or "")
            if not (smtp_host and smtp_user and smtp_password and smtp_from):
                results["email"] = {"success": False, "error": "SMTP не настроен"}
            else:
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "Ваша персональная программа тренировок"
                    msg["From"] = smtp_from
                    msg["To"] = recipient
                    msg.set_content(message or "Во вложении ваша персональная программа тренировок (PDF).")
                    with open(pdf_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                        msg.add_attachment(
                            pdf_bytes,
                            maintype="application",
                            subtype="pdf",
                            filename=os.path.basename(pdf_path),
                        )
                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_password)
                        server.send_message(msg)
                    results["email"] = {"success": True}
                except Exception as exc:
                    logger.error(f"E-mail delivery error: {exc}")
                    results["email"] = {"success": False, "error": str(exc)}

    return results


