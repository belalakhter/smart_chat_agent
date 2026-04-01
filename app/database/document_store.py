from __future__ import annotations

from typing import Any, Optional, TypedDict

from app.database.connection import get_redis

PREFIX = "smart_agent:doc:"
IDS_KEY = f"{PREFIX}ids"


class DocumentRecord(TypedDict):
    id: str
    filename: str
    status: str
    content: bytes


def _meta_key(doc_id: str) -> str:
    return f"{PREFIX}{doc_id}:meta"


def _content_key(doc_id: str) -> str:
    return f"{PREFIX}{doc_id}:content"


def _b(s: str) -> bytes:
    return s.encode("utf-8")


def _decode(v: Any) -> str:
    if isinstance(v, bytes):
        return v.decode("utf-8")
    return str(v)


def create_document(
    doc_id: str,
    filename: str,
    content: bytes,
    status: str = "pending",
) -> None:
    r = get_redis()
    pipe = r.pipeline()
    pipe.sadd(IDS_KEY, _b(doc_id))
    pipe.hset(
        _meta_key(doc_id),
        mapping={
            b"filename": _b(filename),
            b"status": _b(status),
        },
    )
    pipe.set(_content_key(doc_id), content)
    pipe.execute()


def get_document(doc_id: str) -> Optional[DocumentRecord]:
    r = get_redis()
    if not r.sismember(IDS_KEY, _b(doc_id)):
        return None
    meta = r.hgetall(_meta_key(doc_id))
    raw = r.get(_content_key(doc_id))
    if not meta or raw is None:
        return None
    m = {_decode(k): v for k, v in meta.items()}
    return {
        "id": doc_id,
        "filename": _decode(m.get("filename", "")),
        "status": _decode(m.get("status", "")),
        "content": raw if isinstance(raw, bytes) else bytes(raw),
    }


def list_documents() -> list[dict[str, str]]:
    r = get_redis()
    out: list[dict[str, str]] = []
    for raw_id in r.smembers(IDS_KEY):
        doc_id = _decode(raw_id)
        meta = r.hgetall(_meta_key(doc_id))
        if not meta:
            continue
        m = {_decode(k): v for k, v in meta.items()}
        out.append(
            {
                "id": doc_id,
                "filename": _decode(m.get("filename", "")),
                "status": _decode(m.get("status", "")),
            }
        )
    out.sort(key=lambda x: x["id"])
    return out


def delete_document(doc_id: str) -> bool:
    r = get_redis()
    if not r.sismember(IDS_KEY, _b(doc_id)):
        return False
    pipe = r.pipeline()
    pipe.srem(IDS_KEY, _b(doc_id))
    pipe.delete(_meta_key(doc_id), _content_key(doc_id))
    pipe.execute()
    return True


def set_document_status(doc_id: str, status: str) -> bool:
    r = get_redis()
    if not r.sismember(IDS_KEY, _b(doc_id)):
        return False
    r.hset(_meta_key(doc_id), b"status", _b(status))
    return True
