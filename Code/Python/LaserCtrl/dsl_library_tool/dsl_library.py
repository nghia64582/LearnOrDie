"""
Thu vien DSL luu tren Cloudflare Worker KV (REST API), thay cho 1 file
.txt / 1 ban ve trong thu muc.

API cua worker (KV_BASE_URL):
    GET    <base>/<key>  -> {"key": key, "value": <JSON neu parse duoc, neu
                             khong la chuoi>}; key khong ton tai -> 404
                             {"error": "Key not found"}
    POST   <base>/<key>  body = value -> {"success": true, "message": ...}
                             (body rong -> 400)
    DELETE <base>/<key>  -> {"success": true, ...}
Luu y: worker KHONG url-decode key (key = nguyen chuoi path), nen id ban
ve chi dung ky tu an toan [a-z0-9-] (xem slugify) de key luon nhat quan.

Dinh dang key (schema version 1):
    dsl_library:v1:index        -> JSON danh sach ban ve:
        {"schema": "dsl_library.index", "version": 1,
         "updated_at": "2026-10-19T17:40:00Z",
         "drawings": {
             "hw095": {"id": "hw095", "name": "HW095",
                       "description": "...",
                       "key": "dsl_library:v1:file:hw095",
                       "size": 160, "sha256": "...",
                       "updated_at": "..."}}}
    dsl_library:v1:file:<id>    -> JSON 1 ban ve:
        {"schema": "dsl_library.file", "version": 1, "id": "hw095",
         "name": "HW095", "description": "...",
         "content": "<noi dung y het file .txt cu: [NAME]/[DESCRIPTION]/[DSL]>",
         "size": 160, "sha256": "...", "updated_at": "..."}
Gia tri luon la 1 JSON object (khong luu text tron) vi GET tu parse JSON:
text DSL nhu "42" se bi bien thanh so. Boc trong object -> round-trip
khong mat du lieu, "content" giu dung tung byte cua file .txt.

Cache offline: <thu muc thu vien>/.dsl_kv_cache.json luu index + noi dung
da tai, de mo app khi mat mang van xem duoc (chi doc).

Giu nguyen API cu cho main.py: path, list_files(), load(path),
save(path, ...), delete(path), safe_filename(name). "path" cua 1 ban ve
la Path ao <thu muc>/<id>.txt (khong can ton tai tren dia).
"""

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request


# ---- Cau hinh server, sua 1 cho nay ----
KV_BASE_URL = "https://purple-field-d024.nghia64582.workers.dev/"
KV_TIMEOUT = 8  # giay, cho moi request
# Cloudflare chan User-Agent mac dinh "Python-urllib" (error 1010)
KV_USER_AGENT = "LearnOrDie-DSLLibrary/1.0"

KEY_PREFIX = "dsl_library:v1:"
INDEX_KEY = KEY_PREFIX + "index"
FILE_KEY_PREFIX = KEY_PREFIX + "file:"
SCHEMA_VERSION = 1

CACHE_FILENAME = ".dsl_kv_cache.json"


class KVError(Exception):
    """Loi khi goi worker (mat mang, timeout, HTTP loi...)."""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(name):
    # Chuyen ten bat ky thanh id an toan cho key/URL: a-z 0-9 va "-"
    s = name.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:80].strip("-")
    return s or "dsl"


def file_key(dsl_id):
    return FILE_KEY_PREFIX + dsl_id


def parse_sections(text):
    # Tach [NAME]/[DESCRIPTION]/[DSL] tu noi dung text (giong ban cu)
    sections = {"name": "", "description": "", "dsl": ""}
    current = None
    dsl_lines = []

    for line in text.splitlines():
        tag = line.strip()
        if tag == "[NAME]":
            current = "name"
        elif tag == "[DESCRIPTION]":
            current = "description"
        elif tag == "[DSL]":
            current = "dsl"
        elif current == "dsl":
            dsl_lines.append(line)
        elif current:
            if sections[current]:
                sections[current] += "\n" + line
            else:
                sections[current] = line

    sections["dsl"] = "\n".join(dsl_lines)
    return sections


def build_content(name, description, dsl):
    # Dinh dang text giong het ban luu .txt cu
    return (
        "[NAME]\n" + name + "\n\n"
        "[DESCRIPTION]\n" + description + "\n\n"
        "[DSL]\n" + dsl.rstrip() + "\n"
    )


class KVClient:
    def __init__(self, base_url=KV_BASE_URL, timeout=KV_TIMEOUT):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

    def _url(self, key):
        # Key chi gom ky tu an toan nen quote() khong doi gi; van quote
        # de phong, va giu ":" vi worker luu key dung chuoi path
        return self.base_url + urllib.parse.quote(key, safe=":-_.~")

    def _request(self, method, key, body=None):
        data = None if body is None else body.encode("utf-8")
        req = urllib.request.Request(
            self._url(key),
            data=data,
            method=method,
            headers={
                "User-Agent": KV_USER_AGENT,
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as e:
            reason = getattr(e, "reason", e)
            raise KVError(
                f"Cannot reach DSL server {self.base_url} ({reason})"
            ) from e

    def get(self, key):
        """Tra ve value, hoac None neu key khong ton tai (404)."""
        status, text = self._request("GET", key)
        if status == 404:
            return None
        if status != 200:
            raise KVError(f"GET {key} failed: HTTP {status} {text[:200]}")
        try:
            return json.loads(text)["value"]
        except Exception as e:
            raise KVError(f"GET {key}: bad response {text[:200]}") from e

    def post(self, key, value):
        # Luon gui JSON (ensure_ascii -> body chi co ASCII, an toan)
        body = json.dumps(value, ensure_ascii=True)
        status, text = self._request("POST", key, body)
        ok = False
        try:
            ok = status == 200 and json.loads(text).get("success") is True
        except Exception:
            pass
        if not ok:
            raise KVError(f"POST {key} failed: HTTP {status} {text[:200]}")

    def delete(self, key):
        status, text = self._request("DELETE", key)
        if status not in (200, 404):
            raise KVError(f"DELETE {key} failed: HTTP {status} {text[:200]}")


def _empty_index():
    return {
        "schema": "dsl_library.index",
        "version": SCHEMA_VERSION,
        "updated_at": _now(),
        "drawings": {},
    }


class DSLLibrary:
    def __init__(self, path, base_url=KV_BASE_URL):
        # path: thu muc local, dung de luu cache offline va lam nguon
        # import file .txt cu (migrate_txt_files)
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = KVClient(base_url)
        self.cache_path = self.path / CACHE_FILENAME

        self.online = False
        self.last_error = None
        self._cache = self._read_cache()
        self.index = self._cache.get("index") or _empty_index()
        self._loaded = False

    # ---------------- CACHE ----------------

    def _read_cache(self):
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if data.get("version") == SCHEMA_VERSION:
                return data
        except Exception:
            pass
        return {"version": SCHEMA_VERSION, "index": None, "files": {}}

    def _write_cache(self):
        self._cache["index"] = self.index
        self._cache["base_url"] = self.client.base_url
        tmp = self.cache_path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            os.replace(tmp, self.cache_path)
        except Exception:
            pass  # cache chi la phu, loi ghi khong lam hong app

    # ---------------- INDEX ----------------

    def refresh(self):
        """
        Tai lai index tu worker. Loi mang -> dung index trong cache,
        online=False, last_error = thong bao. Tra ve True neu online.
        """
        self._loaded = True
        try:
            index = self.client.get(INDEX_KEY)
        except KVError as e:
            self.online = False
            self.last_error = str(e)
            return False

        if not isinstance(index, dict) or not isinstance(index.get("drawings"), dict):
            index = _empty_index()

        self.index = index
        self.online = True
        self.last_error = None
        self._write_cache()
        return True

    def _ensure_loaded(self):
        if not self._loaded:
            self.refresh()

    def _fresh_index(self):
        # Doc lai index moi nhat ngay truoc khi ghi (read-modify-write).
        # Khong co transaction: 2 may luu cung luc co the de mat 1 entry
        # cua nhau; chi gop entry minh sua vao ban moi nhat de giam rui ro.
        index = self.client.get(INDEX_KEY)
        if not isinstance(index, dict) or not isinstance(index.get("drawings"), dict):
            index = _empty_index()
        return index

    def _write_index(self, index):
        index["schema"] = "dsl_library.index"
        index["version"] = SCHEMA_VERSION
        index["updated_at"] = _now()
        self.client.post(INDEX_KEY, index)
        self.index = index
        self.online = True
        self.last_error = None
        self._write_cache()

    def entries(self):
        """List entry (dict) trong index, sap xep theo ten file (id)."""
        self._ensure_loaded()
        return sorted(self.index["drawings"].values(), key=lambda e: e["id"].lower())

    def list_entries(self):
        """List (path, name, description) de hien thi/tim kiem, khong goi mang."""
        return [(self.path / f"{e['id']}.txt", e.get("name", e["id"]), e.get("description", ""))
                for e in self.entries()]

    def list_files(self):
        return [p for p, _, _ in self.list_entries()]

    # ---------------- LOAD / SAVE / DELETE ----------------

    def _id_of(self, path):
        return Path(path).stem

    def load_content(self, dsl_id):
        """Noi dung text day du cua 1 ban ve (uu tien cache neu dung sha)."""
        self._ensure_loaded()
        entry = self.index["drawings"].get(dsl_id)
        cached = self._cache["files"].get(dsl_id)

        if entry and cached and cached.get("sha256") == entry.get("sha256"):
            return cached["content"]

        try:
            value = self.client.get(file_key(dsl_id))
        except KVError as e:
            self.online = False
            self.last_error = str(e)
            if cached:
                return cached["content"]  # offline: dung ban cache cu
            raise

        if not isinstance(value, dict) or not isinstance(value.get("content"), str):
            raise KVError(f"Drawing '{dsl_id}' not found on server")

        content = value["content"]
        self._cache["files"][dsl_id] = {"sha256": _sha256(content), "content": content}
        self._write_cache()
        return content

    def load(self, path):
        dsl_id = self._id_of(path)
        self._ensure_loaded()
        if dsl_id not in self.index["drawings"] and Path(path).is_file():
            # Tuong thich: file .txt local chua upload len worker
            return parse_sections(Path(path).read_text(encoding="utf-8"))
        return parse_sections(self.load_content(dsl_id))

    def _put(self, dsl_id, content, index):
        # Ghi key ban ve truoc, roi moi cap nhat entry trong index
        sections = parse_sections(content)
        now = _now()
        meta = {
            "id": dsl_id,
            # strip(): ten/mo ta hien thi trong list (load() van tra
            # ve dung nhu ban cu)
            "name": sections["name"].strip(),
            "description": sections["description"].strip(),
            "key": file_key(dsl_id),
            "size": len(content.encode("utf-8")),
            "sha256": _sha256(content),
            "updated_at": now,
        }
        value = dict(meta, schema="dsl_library.file", version=SCHEMA_VERSION,
                     content=content)
        del value["key"]
        self.client.post(file_key(dsl_id), value)
        index["drawings"][dsl_id] = meta
        self._cache["files"][dsl_id] = {"sha256": meta["sha256"], "content": content}

    def save(self, path, name, description, dsl):
        dsl_id = self._id_of(path)
        if slugify(dsl_id) != dsl_id:
            dsl_id = slugify(dsl_id)
        content = build_content(name, description, dsl)

        index = self._fresh_index()
        self._put(dsl_id, content, index)
        self._write_index(index)

    def delete(self, path):
        dsl_id = self._id_of(path)
        index = self._fresh_index()
        index["drawings"].pop(dsl_id, None)
        self._write_index(index)
        self.client.delete(file_key(dsl_id))
        self._cache["files"].pop(dsl_id, None)
        self._write_cache()

    def safe_filename(self, name):
        self._ensure_loaded()
        s = slugify(name)
        ids = set(self.index["drawings"])
        if s not in ids:
            return f"{s}.txt"
        i = 2
        while f"{s}-{i}" in ids:
            i += 1
        return f"{s}-{i}.txt"

    # ---------------- MIGRATION ----------------

    def migrate_txt_files(self, folder=None, overwrite=False):
        """
        Upload cac file *.txt cu (1 file / 1 ban ve) len worker theo dinh
        dang moi. id = slugify(ten file). Neu id da co tren server voi noi
        dung khac thi bo qua (tru khi overwrite=True). Tra ve list
        (ten file, id, trang thai).
        """
        folder = Path(folder) if folder else self.path
        index = self._fresh_index()
        results = []
        used = set()

        for p in sorted(folder.glob("*.txt"), key=lambda p: p.name.lower()):
            # Doc bytes roi decode -> giu nguyen ky tu xuong dong, dung tung byte
            content = p.read_bytes().decode("utf-8")
            dsl_id = slugify(p.stem)
            base, i = dsl_id, 2
            while dsl_id in used:
                dsl_id = f"{base}-{i}"
                i += 1
            used.add(dsl_id)

            old = index["drawings"].get(dsl_id)
            if old and old.get("sha256") == _sha256(content):
                results.append((p.name, dsl_id, "unchanged"))
                continue
            if old and not overwrite:
                results.append((p.name, dsl_id, "skipped (exists, different)"))
                continue

            self._put(dsl_id, content, index)
            results.append((p.name, dsl_id, "uploaded"))

        self._write_index(index)
        return results
