"""Telegram notification channel."""

from __future__ import annotations

import os

import httpx


def send_telegram(message: str, chat_id: str | None = None) -> bool:
    """Send a message via Telegram Bot API.

    Requires TELEGRAM_BOT_TOKEN env var. Chat ID can be passed
    directly or set via TELEGRAM_CHAT_ID env var.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Warning: TELEGRAM_BOT_TOKEN not set, skipping notification")
        return False

    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        print("Warning: No Telegram chat_id configured, skipping notification")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = httpx.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )

    if resp.status_code != 200:
        print(f"Warning: Telegram API returned {resp.status_code}: {resp.text}")
        return False

    return True
