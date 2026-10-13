"""
Simple chat-history storage: each conversation is saved as one JSON file in ./chats
so farmers can reopen earlier conversations after a page refresh.
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

CHATS_DIR = Path(__file__).parent / "chats"
SAFE_ID = re.compile(r"^[\w-]+$")


def new_chat_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


def _path(chat_id: str) -> Path:
    if not SAFE_ID.match(chat_id):
        raise ValueError(f"Invalid chat id: {chat_id}")
    return CHATS_DIR / f"{chat_id}.json"


def save_chat(chat_id: str, messages: list[dict]) -> None:
    """Save a conversation (skipped until the user has asked something)."""
    questions = [m["content"] for m in messages if m["role"] == "user"]
    if not questions:
        return
    CHATS_DIR.mkdir(exist_ok=True)
    path = _path(chat_id)
    now = datetime.now().isoformat(timespec="seconds")
    created = json.loads(path.read_text(encoding="utf-8"))["created"] if path.exists() else now
    title = " ".join(questions[0].split())
    data = {
        "id": chat_id,
        "title": title[:60] + ("…" if len(title) > 60 else ""),
        "created": created,
        "updated": now,
        "messages": messages,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_chat(chat_id: str) -> list[dict]:
    path = _path(chat_id)
    return json.loads(path.read_text(encoding="utf-8"))["messages"] if path.exists() else []


def list_chats() -> list[dict]:
    """All saved chats, newest first (without the message bodies)."""
    if not CHATS_DIR.exists():
        return []
    chats = []
    for path in CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        chats.append({
            "id": data["id"],
            "title": data["title"],
            "updated": data["updated"],
            "count": sum(1 for m in data["messages"] if m["role"] == "user"),
        })
    return sorted(chats, key=lambda c: c["updated"], reverse=True)


def delete_chat(chat_id: str) -> None:
    _path(chat_id).unlink(missing_ok=True)


def delete_all_chats() -> None:
    for path in CHATS_DIR.glob("*.json"):
        path.unlink(missing_ok=True)
