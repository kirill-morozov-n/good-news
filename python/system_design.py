"""
Daily System Design post.
Picks the next topic from system_design_topics.json (round-robin via state file),
asks OpenAI to expand it into a Russian Telegram post, and publishes to the channel.

Source of topics: https://github.com/donnemartin/system-design-primer
"""

import json
import logging
from pathlib import Path

import httpx
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

TOPICS_FILE = Path(__file__).parent / "system_design_topics.json"
STATE_FILE = Path(config.OUTPUT_DIR) / "system_design_state.json"
TG_API = "https://api.telegram.org/bot{token}/{method}"

PRIMER_BASE_URL = "https://github.com/donnemartin/system-design-primer"

SYSTEM_PROMPT = """Ты ведёшь рубрику «System Design» в Telegram-канале для разработчиков уровня middle.

Тебе дают концепцию из system design (название и краткое описание). \
Напиши Telegram-пост на живом, естественном русском — 4–6 предложений, ~600–800 знаков.

Структура поста:
- Первая строка — <b>жирный заголовок</b> с эмодзи в начале (⚙️, 🧱, 🔁, 📡, 🗄️, 🚦 — что подходит)
- Затем суть концепции: что это и зачем
- Один конкретный пример из реальной системы (Netflix, Cloudflare, Discord, AWS, GitHub, Stripe и т.п.) — с цифрами или техническими деталями, если они известны
- Опционально — короткий take или подвох

Форматирование Telegram HTML:
- <b>жирным</b> — ключевые термины (1–2 на пост)
- <i>курсивом</i> — названия компаний, продуктов, протоколов
- <code>моноширинным</code> — команды, идентификаторы, числа с метрикой
- Спецсимволы &, <, > вне тегов — экранируй как &amp; &lt; &gt;

Не пиши «сегодня поговорим», «итак», «давайте разберём» — сразу к делу. \
Не повторяй описание дословно — переработай и добавь живую деталь. \
Выводи только готовый текст поста, без пояснений и без хэштегов в конце (их добавлю отдельно)."""


def _load_topics() -> list[dict]:
    with open(TOPICS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"next_index": 0}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"next_index": 0}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_topic() -> dict:
    """Return the next topic without touching state."""
    topics = _load_topics()
    idx = _load_state().get("next_index", 0) % len(topics)
    return topics[idx]


def pick_topic(advance: bool = True) -> dict:
    """Return the next topic. If advance=True, increment the round-robin pointer."""
    topics = _load_topics()
    state = _load_state()
    idx = state.get("next_index", 0) % len(topics)
    if advance:
        state["next_index"] = (idx + 1) % len(topics)
        _save_state(state)
    return topics[idx]


def build_audio_addendum() -> str:
    """Extra prompt block injected into RESEARCH_PROMPT so the daily audio
    mentions one short system-design tip. Does not advance topic state — the
    text post (later in the day) is what marks the topic as covered.
    """
    topic = _next_topic()
    return (
        "\n\n"
        "ДОПОЛНИТЕЛЬНО — рубрика «System Design (полезность дня)»:\n"
        f"В конце выпуска коротко (≈20 секунд аудио, 2–3 предложения) расскажи "
        f"одну полезную концепцию из system design — тема: <{topic['title']}>. "
        f"Краткая суть: {topic['summary']} "
        "Подай живо, как будто делишься находкой с коллегами; не превращай в лекцию."
    )


async def _generate_post(topic: dict) -> str:
    if not config.OPENAI_API_KEY:
        # Fallback: just use the curated summary
        return f"<b>{topic['title']}</b>\n\n{topic['summary']}"

    user_message = (
        f"Концепция: {topic['title']}\n"
        f"Описание из source: {topic['summary']}"
    )
    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=500,
        temperature=0.6,
    )
    return resp.choices[0].message.content.strip()


def _format_post(body: str, topic: dict) -> str:
    source_url = f"{PRIMER_BASE_URL}#{topic['anchor']}"
    footer = (
        f'\n\n<a href="{source_url}">Источник: system-design-primer →</a>'
        f'\n\n#systemdesign #архитектура'
    )
    # Telegram message limit is 4096 chars; with our short posts we never hit it.
    return body + footer


async def post_system_design() -> bool:
    """Post one system-design topic to Telegram. Returns True on success."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        logger.warning("Telegram not configured — skipping system design post.")
        return False

    topic = pick_topic()
    logger.info("Selected system-design topic: %s", topic["slug"])

    try:
        body = await _generate_post(topic)
    except Exception as e:
        logger.error("OpenAI failed for %s: %s — falling back to summary.", topic["slug"], e)
        body = f"<b>{topic['title']}</b>\n\n{topic['summary']}"

    text = _format_post(body, topic)

    url = TG_API.format(token=config.TELEGRAM_BOT_TOKEN, method="sendMessage")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, data={
                "chat_id": config.TELEGRAM_CHANNEL_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            })
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info("System design posted: %s", topic["title"])
            return True
        logger.error("Telegram error: %s", resp.text)
        return False
    except Exception as e:
        logger.error("Failed to post system design: %s", e)
        return False
