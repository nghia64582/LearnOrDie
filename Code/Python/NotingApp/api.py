import requests
import json
from typing import List, Optional

BASE_URL = "http://nghia64582.online"
HEADERS = {
    "Content-Type": "application/json"
}


# ---------- 1. Create note ----------
def create_note(
    content: str,
    topic_id: Optional[int] = None,
    tags: Optional[List[str]] = None
):
    payload = {
        "content": content,
        "topicId": topic_id,
        "tags": tags or []
    }

    resp = requests.post(
        f"{BASE_URL}/notes",
        headers=HEADERS,
        data=json.dumps(payload)
    )
    resp.raise_for_status()
    return resp.json()


# ---------- 2. Get notes (latest updated, pagination) ----------
def get_notes(offset: int = 0, limit: int = 10):
    params = {
        "offset": offset,
        "limit": limit
    }

    resp = requests.get(
        f"{BASE_URL}/notes",
        params=params
    )
    resp.raise_for_status()
    return resp.json()


# ---------- 3. Get notes by tags ----------
def get_notes_by_tags(
    tags: List[str],
    offset: int = 0,
    limit: int = 10
):
    params = {
        "tags": ",".join(tags),
        "offset": offset,
        "limit": limit
    }

    resp = requests.get(
        f"{BASE_URL}/notes/by-tags",
        params=params
    )
    resp.raise_for_status()
    return resp.json()


# ---------- 4. Get note by ID ----------
def get_note_by_id(note_id: int):
    resp = requests.get(
        f"{BASE_URL}/notes/{note_id}"
    )
    resp.raise_for_status()
    return resp.json()


# ---------- 5. Edit note ----------
def edit_note(
    note_id: int,
    content: str,
    topic_id: Optional[int] = None,
    tags: Optional[List[str]] = None
):
    payload = {
        "content": content,
        "topicId": topic_id,
        "tags": tags or []
    }

    resp = requests.put(
        f"{BASE_URL}/notes/{note_id}",
        headers=HEADERS,
        data=json.dumps(payload)
    )
    resp.raise_for_status()
    return resp.json()


# ---------- Example test flow ----------
if __name__ == "__main__":
    print("=== Create note ===")
    note = create_note(
        content="This is my first note",
        topic_id=None,
        tags=["work", "backend"]
    )
    print(note)
    # to insert row in table, use "IN"

    note_id = note["id"]

    print("\n=== Get note by ID ===")
    note_detail = get_note_by_id(note_id)
    print(note_detail)

    print("\n=== Edit note ===")
    edit_result = edit_note(
        note_id=note_id,
        content="Updated content for this note",
        tags=["mysql", "nodejs"]
    )
    print(edit_result)

    print("\n=== Get notes (pagination) ===")
    notes = get_notes(offset=0, limit=5)
    print(notes)

    print("\n=== Get notes by tags ===")
    notes_by_tags = get_notes_by_tags(
        tags=["mysql", "nodejs"],
        offset=0,
        limit=5
    )
    print(notes_by_tags)
