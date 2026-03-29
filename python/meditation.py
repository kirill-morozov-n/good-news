"""
Evening guided meditation.
Picks a real meditation script, voices it in Russian using edge-tts,
and posts the audio to the Telegram channel.

Pauses are implemented by splitting text into segments, generating audio
for each, inserting silence gaps, and concatenating via ffmpeg.
"""

import asyncio
import json
import logging
import random
import re
import subprocess
import tempfile
from pathlib import Path

from edge_tts import Communicate

import config
import telegram_sender

logger = logging.getLogger(__name__)

MEDITATIONS_FILE = Path(__file__).parent / "meditations.json"
POSTED_FILE = Path(config.OUTPUT_DIR) / "meditation_posted.json"

# Pause durations in seconds
PAUSE_PARAGRAPH = 6  # between paragraphs (\n\n)
PAUSE_ELLIPSIS = 4   # breathing/awareness moment (...)
PAUSE_SENTENCE = 2   # between sentences (. )


def _load_meditations() -> list[dict]:
    with open(MEDITATIONS_FILE, encoding="utf-8") as f:
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


def _pick_meditation() -> tuple[int, dict]:
    """Pick a random meditation that hasn't been posted recently."""
    meditations = _load_meditations()
    posted = _load_posted_indices()
    posted_set = set(posted)
    available = [i for i in range(len(meditations)) if i not in posted_set]
    if not available:
        posted = []
        available = list(range(len(meditations)))
    idx = random.choice(available)
    posted.append(idx)
    keep = max(len(meditations) - len(meditations) // 10, 0)
    _save_posted_indices(posted[-keep:])
    return idx, meditations[idx]


def _split_with_pauses(text: str) -> list[tuple[str, int]]:
    """Split meditation text into (segment, pause_after_seconds) pairs.

    Returns a list where each item is either a text segment to voice
    or a pause duration. Segments are split on paragraph breaks, then
    on ellipses, keeping sentence-level pauses within segments.
    """
    result: list[tuple[str, int]] = []

    # Split on paragraph breaks first
    paragraphs = text.split("\n\n")
    for pi, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        # Split paragraph on ellipsis (...)
        parts = re.split(r'(\.{3})', para)
        for j, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            if part == "...":
                # Add pause for ellipsis
                if result and result[-1][1] < PAUSE_ELLIPSIS:
                    result[-1] = (result[-1][0], PAUSE_ELLIPSIS)
                continue
            result.append((part, PAUSE_SENTENCE))

        # After each paragraph, set a longer pause
        if result and pi < len(paragraphs) - 1:
            result[-1] = (result[-1][0], PAUSE_PARAGRAPH)

    return result


def _generate_silence(duration_s: float, output_path: Path) -> None:
    """Generate a silent MP3 file of given duration using ffmpeg."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=24000:cl=mono",
            "-t", str(duration_s),
            "-c:a", "libmp3lame", "-q:a", "9",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )


async def _generate_audio(text: str, output_path: Path) -> None:
    """Generate meditation MP3 with real silence pauses between segments."""
    segments = _split_with_pauses(text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        file_list: list[str] = []

        for i, (segment_text, pause_s) in enumerate(segments):
            # Generate speech for this segment
            speech_path = tmp / f"seg_{i:03d}_speech.mp3"
            communicate = Communicate(
                segment_text,
                config.MEDITATION_TTS_VOICE,
                rate=config.MEDITATION_TTS_RATE,
            )
            await communicate.save(str(speech_path))
            file_list.append(str(speech_path))

            # Generate silence after segment
            if pause_s > 0:
                silence_path = tmp / f"seg_{i:03d}_silence.mp3"
                _generate_silence(pause_s, silence_path)
                file_list.append(str(silence_path))

        # Write ffmpeg concat list
        concat_file = tmp / "concat.txt"
        with open(concat_file, "w") as f:
            for fp in file_list:
                f.write(f"file '{fp}'\n")

        # Concatenate all segments
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:a", "libmp3lame", "-q:a", "2",
                str(output_path),
            ],
            capture_output=True,
            check=True,
        )

    logger.info("Audio generated: %s", output_path)


async def post_meditation() -> bool:
    """Post one evening meditation to Telegram. Returns True on success."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHANNEL_ID:
        logger.warning("Telegram not configured — skipping meditation.")
        return False

    _, meditation = _pick_meditation()
    title = meditation["title"]
    text = meditation["text"]

    logger.info("Selected meditation: %s", title)

    audio_path = Path(config.OUTPUT_DIR) / "meditation.mp3"
    try:
        await _generate_audio(text, audio_path)
    except Exception as e:
        logger.error("TTS generation failed: %s", e)
        return False

    caption = f"🧘 <b>Вечерняя медитация</b>\n\n{title}\n\n#медитация #вечер"
    ok = await telegram_sender.send_audio(str(audio_path), caption=caption)
    if ok:
        logger.info("Meditation posted: %s", title)
    return ok
