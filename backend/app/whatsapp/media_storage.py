from __future__ import annotations

from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from dataclasses import dataclass
from hashlib import sha256
from os import O_RDONLY, chmod, close, fsync, rename
from os import open as os_open
from pathlib import Path, PurePath
from re import Pattern
from re import compile as compile_pattern
from shutil import rmtree
from stat import S_ISDIR, S_ISREG
from tempfile import mkdtemp
from typing import Protocol
from uuid import UUID

from app.models import WhatsAppMessageType

_STORAGE_KEY_PATTERN: Pattern[str] = compile_pattern(r"v1/[0-9a-f]{32}")
_METADATA_FILENAME = "metadata"
_CONTENT_FILENAME = "content"
_METADATA_VERSION = "1"
_MAX_METADATA_BYTES = 4_096


@dataclass(frozen=True, slots=True)
class MediaPutRequest:
    media_ref: UUID
    content: bytes
    media_type: WhatsAppMessageType
    mime_type: str
    filename: str | None


@dataclass(frozen=True, slots=True)
class StoredMedia:
    media_ref: UUID
    storage_key: str
    media_type: WhatsAppMessageType
    mime_type: str
    filename: str | None
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class StoredMediaContent:
    metadata: StoredMedia
    content: bytes


class MediaStorageError(Exception):
    """Safe storage-boundary error suitable for application reconciliation."""


class MediaStorageConflictError(MediaStorageError):
    """Raised when one media reference is reused for different content."""


class MediaStorageIntegrityError(MediaStorageError):
    """Raised when durable content does not match its private metadata."""


class MediaStorageNotFoundError(MediaStorageError):
    """Raised when a private media object cannot be resolved."""


class MediaStorage(Protocol):
    def put(self, request: MediaPutRequest) -> StoredMedia: ...

    def get(self, storage_key: str) -> StoredMediaContent: ...

    def get_metadata(self, media_ref: UUID) -> StoredMedia: ...


class FakeMediaStorage:
    def __init__(self) -> None:
        self._items: dict[str, StoredMediaContent] = {}
        self._keys_by_reference: dict[UUID, str] = {}
        self._put_error: str | None = None

    def configure_put_failure(self, safe_message: str | None) -> None:
        self._put_error = safe_message

    def put(self, request: MediaPutRequest) -> StoredMedia:
        if self._put_error is not None:
            raise MediaStorageError(self._put_error)
        existing_key = self._keys_by_reference.get(request.media_ref)
        if existing_key is not None:
            existing = self.get(existing_key)
            _assert_matching_request(existing, request)
            return existing.metadata
        storage_key = f"fake-media-{len(self._items) + 1:06d}"
        metadata = _stored_media(request, storage_key)
        self._items[storage_key] = StoredMediaContent(
            metadata=metadata,
            content=request.content,
        )
        self._keys_by_reference[request.media_ref] = storage_key
        return metadata

    def get(self, storage_key: str) -> StoredMediaContent:
        try:
            stored = self._items[storage_key]
        except KeyError as error:
            raise MediaStorageNotFoundError("Stored media was not found") from error
        _verify_content(stored)
        return stored

    def get_metadata(self, media_ref: UUID) -> StoredMedia:
        storage_key = self._keys_by_reference.get(media_ref)
        if storage_key is None:
            raise MediaStorageNotFoundError("Stored media reference was not found")
        return self.get(storage_key).metadata


class FilesystemMediaStorage:
    def __init__(self, root: Path) -> None:
        if root.exists() and root.is_symlink():
            raise MediaStorageError("Media storage root cannot be a symbolic link")
        try:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            chmod(root, 0o700)
            self._root = root.resolve(strict=True)
            self._objects_root = self._root / "v1"
            self._objects_root.mkdir(mode=0o700, exist_ok=True)
            chmod(self._objects_root, 0o700)
            self._assert_directory(self._root)
            self._assert_directory(self._objects_root)
        except OSError as error:
            raise MediaStorageError("Media storage root is unavailable") from error

    def put(self, request: MediaPutRequest) -> StoredMedia:
        _validate_put_request(request)
        storage_key = _storage_key(request.media_ref)
        target = self._object_directory(storage_key)
        if target.exists():
            existing = self.get(storage_key)
            _assert_matching_request(existing, request)
            return existing.metadata

        temporary = Path(mkdtemp(prefix=".tmp-", dir=self._objects_root))
        try:
            chmod(temporary, 0o700)
            metadata = _stored_media(request, storage_key)
            self._write_file(temporary / _CONTENT_FILENAME, request.content)
            self._write_file(
                temporary / _METADATA_FILENAME,
                _encode_metadata(metadata),
            )
            self._before_promote(temporary)
            try:
                rename(temporary, target)
            except OSError:
                if not target.exists():
                    raise
                existing = self.get(storage_key)
                _assert_matching_request(existing, request)
                return existing.metadata
            else:
                self._sync_directory(self._objects_root)
                return metadata
        except MediaStorageError:
            raise
        except OSError as error:
            raise MediaStorageError("Media storage write failed") from error
        finally:
            if temporary.exists():
                rmtree(temporary)

    def get(self, storage_key: str) -> StoredMediaContent:
        metadata = self._read_metadata(storage_key)
        object_directory = self._object_directory(storage_key)
        content_path = object_directory / _CONTENT_FILENAME
        try:
            self._assert_regular_file(content_path)
            if content_path.stat().st_size != metadata.size_bytes:
                raise MediaStorageIntegrityError("Stored media length is invalid")
            content = content_path.read_bytes()
        except MediaStorageError:
            raise
        except OSError as error:
            raise MediaStorageNotFoundError(
                "Stored media content is unavailable"
            ) from error
        stored = StoredMediaContent(metadata=metadata, content=content)
        _verify_content(stored)
        return stored

    def get_metadata(self, media_ref: UUID) -> StoredMedia:
        return self._read_metadata(_storage_key(media_ref))

    def _read_metadata(self, storage_key: str) -> StoredMedia:
        object_directory = self._object_directory(storage_key)
        metadata_path = object_directory / _METADATA_FILENAME
        try:
            self._assert_directory(object_directory)
            self._assert_regular_file(metadata_path)
            if metadata_path.stat().st_size > _MAX_METADATA_BYTES:
                raise MediaStorageIntegrityError("Stored media metadata is invalid")
            metadata = _decode_metadata(metadata_path.read_bytes())
        except MediaStorageError:
            raise
        except OSError as error:
            raise MediaStorageNotFoundError(
                "Stored media metadata is unavailable"
            ) from error
        if metadata.storage_key != storage_key:
            raise MediaStorageIntegrityError("Stored media key is invalid")
        if _storage_key(metadata.media_ref) != storage_key:
            raise MediaStorageIntegrityError("Stored media reference is invalid")
        content_path = object_directory / _CONTENT_FILENAME
        try:
            self._assert_regular_file(content_path)
            if content_path.stat().st_size != metadata.size_bytes:
                raise MediaStorageIntegrityError("Stored media length is invalid")
        except MediaStorageError:
            raise
        except OSError as error:
            raise MediaStorageNotFoundError(
                "Stored media content is unavailable"
            ) from error
        return metadata

    def _object_directory(self, storage_key: str) -> Path:
        self._assert_directory(self._root)
        self._assert_directory(self._objects_root)
        if _STORAGE_KEY_PATTERN.fullmatch(storage_key) is None:
            raise MediaStorageNotFoundError("Stored media key is invalid")
        identifier = storage_key.removeprefix("v1/")
        candidate = self._objects_root / identifier
        if candidate.parent != self._objects_root:
            raise MediaStorageNotFoundError("Stored media key is invalid")
        return candidate

    @staticmethod
    def _write_file(path: Path, content: bytes) -> None:
        with path.open("xb") as file_handle:
            chmod(path, 0o600)
            file_handle.write(content)
            file_handle.flush()
            fsync(file_handle.fileno())

    @staticmethod
    def _sync_directory(path: Path) -> None:
        descriptor = os_open(path, O_RDONLY)
        try:
            fsync(descriptor)
        finally:
            close(descriptor)

    @staticmethod
    def _assert_directory(path: Path) -> None:
        try:
            mode = path.lstat().st_mode
        except OSError as error:
            raise MediaStorageNotFoundError(
                "Media storage directory is unavailable"
            ) from error
        if path.is_symlink() or not S_ISDIR(mode):
            raise MediaStorageError("Media storage directory is invalid")

    @staticmethod
    def _assert_regular_file(path: Path) -> None:
        try:
            mode = path.lstat().st_mode
        except OSError as error:
            raise MediaStorageNotFoundError(
                "Stored media file is unavailable"
            ) from error
        if path.is_symlink() or not S_ISREG(mode):
            raise MediaStorageIntegrityError("Stored media file is invalid")

    def _before_promote(self, temporary: Path) -> None:
        del temporary


def _stored_media(request: MediaPutRequest, storage_key: str) -> StoredMedia:
    return StoredMedia(
        media_ref=request.media_ref,
        storage_key=storage_key,
        media_type=request.media_type,
        mime_type=request.mime_type,
        filename=request.filename,
        size_bytes=len(request.content),
        sha256=sha256(request.content).hexdigest(),
    )


def _validate_put_request(request: MediaPutRequest) -> None:
    if not request.content:
        raise MediaStorageError("Stored media cannot be empty")
    if request.media_type not in {
        WhatsAppMessageType.IMAGE,
        WhatsAppMessageType.DOCUMENT,
    }:
        raise MediaStorageError("Stored media type is invalid")
    if not request.mime_type or request.mime_type != request.mime_type.strip().lower():
        raise MediaStorageError("Stored media MIME type is invalid")
    if request.filename is not None:
        leaf = PurePath(request.filename.replace("\\", "/")).name
        if leaf != request.filename or not all(
            character.isprintable() for character in request.filename
        ):
            raise MediaStorageError("Stored media filename is invalid")


def _assert_matching_request(
    existing: StoredMediaContent,
    request: MediaPutRequest,
) -> None:
    expected = _stored_media(request, existing.metadata.storage_key)
    if existing.metadata != expected or existing.content != request.content:
        raise MediaStorageConflictError(
            "Media reference is already used for different content"
        )


def _verify_content(stored: StoredMediaContent) -> None:
    if len(stored.content) != stored.metadata.size_bytes:
        raise MediaStorageIntegrityError("Stored media length is invalid")
    if sha256(stored.content).hexdigest() != stored.metadata.sha256:
        raise MediaStorageIntegrityError("Stored media checksum is invalid")


def _storage_key(media_ref: UUID) -> str:
    return f"v1/{media_ref.hex}"


def _encode_metadata(metadata: StoredMedia) -> bytes:
    filename = "" if metadata.filename is None else _encoded(metadata.filename)
    values = (
        _METADATA_VERSION,
        str(metadata.media_ref),
        metadata.storage_key,
        metadata.media_type.value,
        _encoded(metadata.mime_type),
        filename,
        str(metadata.size_bytes),
        metadata.sha256,
    )
    return ("\n".join(values) + "\n").encode("ascii")


def _decode_metadata(content: bytes) -> StoredMedia:
    try:
        values = content.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise MediaStorageIntegrityError("Stored media metadata is invalid") from error
    if len(values) != 8 or values[0] != _METADATA_VERSION:
        raise MediaStorageIntegrityError("Stored media metadata is invalid")
    try:
        media_ref = UUID(values[1])
        storage_key = values[2]
        media_type = WhatsAppMessageType(values[3])
        mime_type = _decoded(values[4])
        filename = _decoded(values[5]) if values[5] else None
        size_bytes = int(values[6])
        checksum = values[7]
    except (Base64Error, UnicodeDecodeError, ValueError) as error:
        raise MediaStorageIntegrityError("Stored media metadata is invalid") from error
    if (
        size_bytes <= 0
        or len(checksum) != 64
        or any(character not in "0123456789abcdef" for character in checksum)
        or media_type not in {WhatsAppMessageType.IMAGE, WhatsAppMessageType.DOCUMENT}
        or not mime_type
        or mime_type != mime_type.strip().lower()
    ):
        raise MediaStorageIntegrityError("Stored media metadata is invalid")
    metadata = StoredMedia(
        media_ref=media_ref,
        storage_key=storage_key,
        media_type=media_type,
        mime_type=mime_type,
        filename=filename,
        size_bytes=size_bytes,
        sha256=checksum,
    )
    _validate_metadata_filename(metadata.filename)
    return metadata


def _encoded(value: str) -> str:
    return urlsafe_b64encode(value.encode("utf-8")).decode("ascii")


def _decoded(value: str) -> str:
    return b64decode(value, altchars=b"-_", validate=True).decode("utf-8")


def _validate_metadata_filename(filename: str | None) -> None:
    if filename is None:
        return
    leaf = PurePath(filename.replace("\\", "/")).name
    if leaf != filename or not all(character.isprintable() for character in filename):
        raise MediaStorageIntegrityError("Stored media filename is invalid")
