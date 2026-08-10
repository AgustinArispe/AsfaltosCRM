from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoreMediaRequest:
    content: bytes
    mime_type: str
    filename: str | None


@dataclass(frozen=True, slots=True)
class StoredMedia:
    storage_key: str
    mime_type: str
    filename: str | None
    size_bytes: int


@dataclass(frozen=True, slots=True)
class StoredMediaContent:
    content: bytes
    mime_type: str
    filename: str | None


class MediaStorageError(Exception):
    """Safe storage-boundary error suitable for application reconciliation."""


class MediaStorage(Protocol):
    def store(self, request: StoreMediaRequest) -> StoredMedia: ...

    def read(self, storage_key: str) -> StoredMediaContent: ...

    def delete(self, storage_key: str) -> None: ...


class FakeMediaStorage:
    def __init__(self) -> None:
        self._next_key = 1
        self._items: dict[str, StoredMediaContent] = {}
        self._store_error: str | None = None

    def configure_store_failure(self, safe_message: str | None) -> None:
        self._store_error = safe_message

    def store(self, request: StoreMediaRequest) -> StoredMedia:
        if self._store_error is not None:
            raise MediaStorageError(self._store_error)
        storage_key = f"fake-media-{self._next_key:06d}"
        self._next_key += 1
        self._items[storage_key] = StoredMediaContent(
            content=request.content,
            mime_type=request.mime_type,
            filename=request.filename,
        )
        return StoredMedia(
            storage_key=storage_key,
            mime_type=request.mime_type,
            filename=request.filename,
            size_bytes=len(request.content),
        )

    def read(self, storage_key: str) -> StoredMediaContent:
        try:
            return self._items[storage_key]
        except KeyError as error:
            raise FileNotFoundError(storage_key) from error

    def delete(self, storage_key: str) -> None:
        self._items.pop(storage_key, None)
