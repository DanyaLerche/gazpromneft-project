from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from config import settings


def _send_sync(*, recipient: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message.set_content(body)

    host = settings.SMTP_HOST.strip()
    if not host:
        raise RuntimeError("SMTP_HOST is not configured")

    smtp_cls = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    with smtp_cls(host, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as smtp:
        if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)


async def send_email(*, recipient: str, subject: str, body: str) -> None:
    await asyncio.to_thread(_send_sync, recipient=recipient, subject=subject, body=body)
