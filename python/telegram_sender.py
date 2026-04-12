"""
Sends generated audio to a Telegram channel via Bot API.
Uses httpx (already a dependency of notebooklm-py).
"""

import logging
from pathlib import Path

import httpx

import config

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"


async def send_audio(audio_path: str, caption: str = "") -> bool:
    """Upload audio file to the configured Telegram channel.

    Returns True on success, False on failure.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        logger.warning("Telegram not configured — skipping upload.")
        return False

    path = Path(audio_path)
    if not path.exists():
        logger.error("Audio file not found: %s", audio_path)
        return False

    thumb_path = Path(__file__).resolve().parent.parent / "assets" / "logo_audio.png"

    if thumb_path.exists():
        photo_url = API_BASE.format(token=config.TELEGRAM_BOT_TOKEN, method="sendPhoto")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                with open(thumb_path, "rb") as pf:
                    resp = await client.post(
                        photo_url,
                        data={"chat_id": config.TELEGRAM_CHANNEL_ID},
                        files={"photo": (thumb_path.name, pf, "image/png")},
                    )
            if resp.status_code == 200 and resp.json().get("ok"):
                logger.info("Cover photo sent.")
            else:
                logger.error("sendPhoto failed: %s", resp.text)
        except Exception as exc:
            logger.error("Failed to send cover photo: %s", exc)

    url = API_BASE.format(token=config.TELEGRAM_BOT_TOKEN, method="sendAudio")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            with open(path, "rb") as f:
                files = {"audio": (path.name, f, "audio/mpeg")}
                thumb_f = None
                if thumb_path.exists():
                    thumb_f = open(thumb_path, "rb")
                    files["thumbnail"] = (thumb_path.name, thumb_f, "image/png")
                try:
                    response = await client.post(
                        url,
                        data={
                            "chat_id": config.TELEGRAM_CHANNEL_ID,
                            "caption": caption,
                            "parse_mode": "HTML",
                        },
                        files=files,
                    )
                finally:
                    if thumb_f is not None:
                        thumb_f.close()

        if response.status_code == 200 and response.json().get("ok"):
            logger.info("Audio sent to Telegram channel %s.", config.TELEGRAM_CHANNEL_ID)
            return True
        else:
            logger.error("Telegram API error: %s", response.text)
            return False

    except Exception as exc:
        logger.error("Failed to send audio to Telegram: %s", exc)
        return False
