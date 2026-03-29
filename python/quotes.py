"""
Daily quotes from yoga, tantra, and Buddhism.
Posts a random quote (translated to Russian) to the Telegram channel, avoiding recent repeats.
Quotes sourced from Quotes-500K dataset (Goodreads).
"""

import json
import logging
import random
from pathlib import Path

import httpx
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

QUOTES_FILE = Path(__file__).parent / "spiritual_quotes.json"
POSTED_FILE = Path(config.OUTPUT_DIR) / "quotes_posted.json"
TG_API = "https://api.telegram.org/bot{token}/{method}"


def _load_quotes() -> list[dict]:
    with open(QUOTES_FILE, encoding="utf-8") as f:
        return json.load(f)


def _load_posted_indices() -> list[int]:
    if not POSTED_FILE.exists():
        return []
    try:
        return json.loads(POSTED_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_posted_indices(indices: list[int]) -> None:
    POSTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    POSTED_FILE.write_text(json.dumps(indices), encoding="utf-8")


def _pick_quote() -> dict:
    """Pick a random quote that hasn't been posted recently."""
    quotes = _load_quotes()
    posted = _load_posted_indices()
    posted_set = set(posted)
    available = [i for i in range(len(quotes)) if i not in posted_set]
    if not available:
        # All posted — reset and start over
        posted = []
        available = list(range(len(quotes)))
    idx = random.choice(available)
    posted.append(idx)
    # Keep history at 90% of total to ensure rotation
    keep = max(len(quotes) - len(quotes) // 10, 0)
    _save_posted_indices(posted[-keep:])
    return quotes[idx]


async def _translate_quote(text: str) -> str:
    """Translate a quote to Russian using OpenAI."""
    if not config.OPENAI_API_KEY:
        return text
    try:
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "Переведи цитату на красивый, естественный русский язык. "
                    "Сохрани глубину и поэтичность оригинала. "
                    "Выведи только перевод, без пояснений и кавычек."
                )},
                {"role": "user", "content": text},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Quote translation failed: %s", e)
        return text


def _format_quote(text: str, author: str) -> str:
    return (
        f"🪷 <i>«{text}»</i>\n\n"
        f"— <b>{author}</b>\n\n"
        f"#мудрость #цитата"
    )


async def post_quote() -> bool:
    """Post one quote to Telegram. Returns True on success."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        logger.warning("Telegram not configured — skipping quote.")
        return False

    quote = _pick_quote()
    translated = await _translate_quote(quote["text"])
    text = _format_quote(translated, quote["author"])

    url = TG_API.format(token=config.TELEGRAM_BOT_TOKEN, method="sendMessage")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data={
                "chat_id": config.TELEGRAM_CHANNEL_ID,
                "text": text,
                "parse_mode": "HTML",
            })
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info("Quote posted: %s — %s", quote["author"], quote["text"][:50])
            return True
        logger.error("Telegram error: %s", resp.text)
        return False
    except Exception as e:
        logger.error("Failed to post quote: %s", e)
        return False
