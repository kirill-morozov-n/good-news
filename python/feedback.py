"""
Feedback loop: poll Telegram channel reactions and generate calibration reports.

Architecture:
  - poll_reactions() — call Telegram getUpdates with allowed_updates=["message_reaction_count"],
    persist tally per message_id in output/reactions.json. last_update_id in output/feedback_state.json.
  - generate_report() — join rss_posted.json.message_log with reactions.json, write
    output/feedback_report.csv, print top-5/by-feed/by-category summary, and post that
    summary to TELEGRAM_ADMIN_CHAT_ID if configured.
"""

import asyncio
import csv
import json
import logging
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import httpx

import config

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"

REACTIONS_FILE = Path(config.OUTPUT_DIR) / "reactions.json"
STATE_FILE = Path(config.OUTPUT_DIR) / "feedback_state.json"
POSTED_FILE = Path(config.OUTPUT_DIR) / "rss_posted.json"
REPORT_CSV = Path(config.OUTPUT_DIR) / "feedback_report.csv"

LIKE = "👍"
DISLIKE = "👎"


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to read %s: %s — using default.", path, e)
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict:
    return _read_json(STATE_FILE, {"last_update_id": 0})


def save_state(state: dict) -> None:
    _write_json(STATE_FILE, state)


def load_reactions() -> dict:
    return _read_json(REACTIONS_FILE, {})


def save_reactions(reactions: dict) -> None:
    _write_json(REACTIONS_FILE, reactions)


def load_message_log() -> list[dict]:
    data = _read_json(POSTED_FILE, {})
    if isinstance(data, list):  # very old format
        return []
    return data.get("message_log", []) or []


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

async def poll_reactions() -> int:
    """Fetch new message_reaction_count updates from Telegram, update reactions.json.

    Returns the number of updates processed.
    """
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping reaction poll.")
        return 0

    state = load_state()
    last_seen = int(state.get("last_update_id") or 0)
    offset = last_seen + 1 if last_seen else 0

    url = API_BASE.format(token=config.TELEGRAM_BOT_TOKEN, method="getUpdates")
    params = {
        "offset": offset,
        "timeout": 0,  # no long-poll — return immediately
        "allowed_updates": json.dumps(["message_reaction_count"]),
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
    except Exception as e:
        logger.error("getUpdates request failed: %s", e)
        return 0

    if resp.status_code != 200:
        logger.error("getUpdates HTTP %s: %s", resp.status_code, resp.text[:300])
        return 0

    body = resp.json()
    if not body.get("ok"):
        logger.error("getUpdates not OK: %s", body)
        return 0

    updates = body.get("result", []) or []
    if not updates:
        logger.info("poll-reactions: no new updates (offset=%s).", offset)
        return 0

    reactions = load_reactions()
    max_uid = last_seen
    target_chat = str(config.TELEGRAM_CHANNEL_ID)
    for upd in updates:
        max_uid = max(max_uid, int(upd.get("update_id", 0)))
        mrc = upd.get("message_reaction_count")
        if not mrc:
            continue
        chat = mrc.get("chat") or {}
        if str(chat.get("id")) != target_chat:
            # Reactions on some other chat — ignore.
            continue
        mid = mrc.get("message_id")
        if mid is None:
            continue
        counts: dict[str, int] = {}
        for r in mrc.get("reactions", []) or []:
            t = r.get("type") or {}
            emoji = t.get("emoji") or t.get("custom_emoji_id") or "?"
            counts[emoji] = int(r.get("total_count") or 0)
        counts["updated_at"] = datetime.utcnow().isoformat() + "Z"
        reactions[str(mid)] = counts

    save_reactions(reactions)
    state["last_update_id"] = max_uid
    save_state(state)
    logger.info(
        "poll-reactions: processed %d update(s), last_update_id=%s.",
        len(updates), max_uid,
    )
    return len(updates)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _category_of(hashtags: str) -> str:
    """First hashtag = rough category."""
    return (hashtags or "").split()[0] if hashtags else "(no-tag)"


def _build_rows() -> list[dict]:
    """Join message_log with reactions.json into flat rows."""
    log = load_message_log()
    reactions = load_reactions()
    rows = []
    for entry in log:
        mid = str(entry.get("mid"))
        r = reactions.get(mid, {}) or {}
        likes = int(r.get(LIKE, 0))
        dislikes = int(r.get(DISLIKE, 0))
        rows.append({
            "ts": entry.get("ts", ""),
            "mid": mid,
            "category": _category_of(entry.get("hashtags", "")),
            "hashtags": entry.get("hashtags", ""),
            "feed_url": entry.get("feed_url", ""),
            "article_url": entry.get("article_url", ""),
            "title": entry.get("title", ""),
            "likes": likes,
            "dislikes": dislikes,
            "score": likes - dislikes,
        })
    return rows


def _write_csv(rows: list[dict]) -> None:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["ts", "mid", "category", "hashtags", "feed_url",
                  "article_url", "title", "likes", "dislikes", "score"]
    with REPORT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _summary_text(rows: list[dict]) -> str:
    """Build a compact HTML summary for Telegram admin chat."""
    rated = [r for r in rows if r["likes"] or r["dislikes"]]
    n_total = len(rows)
    n_rated = len(rated)

    if n_rated == 0:
        return (
            "📊 <b>Feedback report</b>\n\n"
            f"Постов в логе: {n_total}\n"
            "Постов с реакциями: 0 — данных пока нет."
        )

    # Top 5 liked, top 5 disliked
    top_liked = sorted(rated, key=lambda r: (-r["likes"], r["dislikes"]))[:5]
    top_disliked = sorted(rated, key=lambda r: (-r["dislikes"], -r["likes"]))[:5]

    # By feed
    feed_agg: dict[str, list[int]] = defaultdict(list)
    for r in rated:
        feed_agg[r["feed_url"] or "(unknown)"].append(r["score"])
    feed_summary = sorted(
        ((url, sum(s) / len(s), len(s)) for url, s in feed_agg.items()),
        key=lambda x: (x[1], x[2]),
    )

    # By category
    cat_agg: dict[str, list[int]] = defaultdict(list)
    for r in rated:
        cat_agg[r["category"]].append(r["score"])
    cat_summary = sorted(
        ((c, sum(s) / len(s), len(s)) for c, s in cat_agg.items()),
        key=lambda x: -x[1],
    )

    def _esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _trim(s: str, n: int = 70) -> str:
        s = s or ""
        return s if len(s) <= n else s[: n - 1] + "…"

    lines = [
        "📊 <b>Feedback report</b>",
        "",
        f"Постов в логе: <b>{n_total}</b>",
        f"С реакциями: <b>{n_rated}</b>",
        "",
        "<b>👍 Топ-5 понравившихся</b>",
    ]
    for r in top_liked:
        lines.append(f"  +{r['likes']}/-{r['dislikes']} <i>{_esc(_trim(r['title']))}</i>")
    lines += ["", "<b>👎 Топ-5 непонравившихся</b>"]
    for r in top_disliked:
        lines.append(f"  +{r['likes']}/-{r['dislikes']} <i>{_esc(_trim(r['title']))}</i>")
    lines += ["", "<b>По категориям (avg score)</b>"]
    for cat, avg, n in cat_summary[:8]:
        lines.append(f"  {_esc(cat)}: {avg:+.2f} ({n})")
    lines += ["", "<b>Худшие фиды (avg score)</b>"]
    for url, avg, n in feed_summary[:5]:
        lines.append(f"  {avg:+.2f} ({n}) — {_esc(_trim(url, 60))}")

    return "\n".join(lines)


async def _post_summary_to_admin(text: str) -> None:
    admin_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
    if not admin_id or not config.TELEGRAM_BOT_TOKEN:
        logger.info("Admin summary skipped (TELEGRAM_ADMIN_CHAT_ID or token unset).")
        return
    url = API_BASE.format(token=config.TELEGRAM_BOT_TOKEN, method="sendMessage")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                data={
                    "chat_id": admin_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": "true",
                },
            )
        if resp.status_code != 200 or not resp.json().get("ok"):
            logger.error("Admin summary post failed: %s", resp.text[:300])
    except Exception as e:
        logger.error("Admin summary post exception: %s", e)


async def generate_report() -> None:
    rows = _build_rows()
    _write_csv(rows)
    logger.info("Wrote %s with %d rows.", REPORT_CSV, len(rows))
    summary = _summary_text(rows)
    print(summary)
    await _post_summary_to_admin(summary)


# ---------------------------------------------------------------------------
# Entrypoints used by main.py
# ---------------------------------------------------------------------------

async def cmd_poll_reactions() -> None:
    await poll_reactions()


async def cmd_feedback_report() -> None:
    await generate_report()


if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else "report"
    if arg == "poll":
        asyncio.run(cmd_poll_reactions())
    else:
        asyncio.run(cmd_feedback_report())
