"""
Sends generated audio to a Telegram channel via Bot API.
Uses httpx (already a dependency of notebooklm-py).
"""

import asyncio
import logging
import shutil
from pathlib import Path

import httpx

import config

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"

# Telegram Bot API limit for sendAudio multipart upload is 50 MB. Stay below
# with margin for headers and Telegram's accounting.
MAX_AUDIO_BYTES = 48 * 1024 * 1024


async def _compress_audio(src: Path) -> Path | None:
    """Re-encode audio to fit under MAX_AUDIO_BYTES.

    Tries 64 kbps mono first, then 48 kbps if still too large. Returns the
    compressed path, or None if ffmpeg is unavailable / compression failed.
    """
    if shutil.which("ffmpeg") is None:
        logger.error("ffmpeg not installed — cannot compress oversized audio.")
        return None

    for bitrate in ("64k", "48k"):
        dst = src.with_name(f"{src.stem}_compressed_{bitrate}{src.suffix}")
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-vn", "-ac", "1", "-b:a", bitrate,
            "-codec:a", "libmp3lame",
            str(dst),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0:
            logger.error("ffmpeg failed (%s): %s", bitrate, err.decode(errors="ignore")[:500])
            continue
        size = dst.stat().st_size
        logger.info("Compressed audio at %s: %.1f MB", bitrate, size / 1024 / 1024)
        if size <= MAX_AUDIO_BYTES:
            return dst
    return None


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

    # Pre-flight: if the file is over Telegram's 50 MB sendAudio limit,
    # re-encode at lower bitrate so the upload succeeds.
    if path.stat().st_size > MAX_AUDIO_BYTES:
        logger.info(
            "Audio %.1f MB exceeds Telegram limit — compressing.",
            path.stat().st_size / 1024 / 1024,
        )
        compressed = await _compress_audio(path)
        if compressed is None:
            logger.error("Audio too large and compression unavailable — aborting upload.")
            return False
        path = compressed

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
