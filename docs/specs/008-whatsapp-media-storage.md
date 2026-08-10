# CRM-008 — WhatsApp Media Storage

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-08-10
Implementation commit: 4a4fc9f

## Goal

Provide a production-ready, provider-agnostic storage boundary for WhatsApp images and
PDF/documents without coupling domain or API code to a filesystem or cloud vendor.

## Context

CRM-005 defines attachment metadata and storage states. CRM-006 defines authenticated
upload and content contracts using opaque `media_ref` values. This spec replaces the
in-memory-only storage lifecycle with durable local storage while preserving those
behaviors and public API contracts.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API

## Scope

- Finalize the strictly typed `MediaStorage` boundary and adapt `FakeMediaStorage` to
  it.
- Add a private filesystem-backed adapter for local Docker development.
- Persist uploaded bytes and private metadata across backend container restarts.
- Apply configurable media limits, trusted content validation, integrity checks, and
  safe storage-failure reconciliation.
- Define, but do not implement, the compatibility requirements for a future S3-style
  object-storage adapter.

## Non-goals

- Frontend changes or changes to CRM-006 public routes and payloads.
- Meta media API upload/download or any provider-specific limit.
- An S3 adapter, deployment credentials, CDN, public URLs, or public storage access.
- Image processing, resizing, transcoding, thumbnails, or content editing.
- Antivirus scanning unless separately approved.
- Audio, video, or other message types outside CRM-005.
- Legal retention/anonymization policy or a normal media hard-delete workflow.

## Business rules

- Media remains limited to CRM-005 `IMAGE` and `DOCUMENT`; PDF is the required V1
  document format.
- WhatsApp media attached to a message is commercial history. Customer or Opportunity
  soft deletion does not remove it, and there is no normal hard-delete operation.
- CRM-005 remains the source of `PENDING`, `AVAILABLE`, and `FAILED` attachment
  behavior. CRM-008 defines only storage-boundary effects and retry mechanics.
- CRM-006 remains the sole client-facing boundary: media access is authenticated,
  `media_ref` stays opaque, and binary content is never embedded as base64 in JSON.

## Data model

No new table or migration is required. Existing attachment fields remain authoritative:
`storage_key`, `storage_status`, `storage_error`, `mime_type`, `filename`, and
`size_bytes`.

The storage adapter durably associates each server-generated UUID `media_ref` with one
private object and its metadata. `media_ref` is not serialized as a filesystem path or
raw `storage_key`. The adapter metadata includes the internal key, normalized MIME type,
sanitized filename, byte length, and SHA-256 checksum. This replaces the process-local
upload registry for lookup after restart without changing CRM-006 responses.

No checksum column is required in PostgreSQL in this scope. The adapter owns and
verifies its private checksum metadata; the attachment row continues to hold the
business-facing storage evidence defined by CRM-005.

## Contracts / API

The final internal boundary uses immutable, explicitly typed DTOs equivalent to:

```python
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


class MediaStorage(Protocol):
    def put(self, request: MediaPutRequest) -> StoredMedia: ...
    def get(self, storage_key: str) -> StoredMediaContent: ...
    def get_metadata(self, media_ref: UUID) -> StoredMedia: ...
```

`get_metadata` is justified because CRM-006 must resolve an opaque upload reference
after a process or container restart. It must not return bytes. `delete` is intentionally
absent: partial temporary-file cleanup is an adapter responsibility, and no approved
application workflow deletes historical media.

`put` is idempotent for the same `media_ref` and identical validated content. Reusing
that reference with different content or metadata is a safe storage conflict. A normal
second upload receives a new `media_ref` and object; content deduplication is not
performed implicitly.

CRM-006 remains unchanged:

- `POST /api/whatsapp/media` returns an opaque `media_ref` only after durable storage
  succeeds.
- authenticated preview and attachment endpoints continue streaming through FastAPI;
  they never return keys, paths, object URLs, or base64.
- outbound media requests continue referencing `media_ref`, which is resolved with
  `get_metadata` before CRM-005 dispatch.

## State transitions

### Outbound upload

1. The application allocates a cryptographically random UUID `media_ref`.
2. It validates declared type, detected content, size, and filename before `put`.
3. The adapter atomically stores content and private metadata.
4. Only a successful durable `put` produces the CRM-006 upload response. Storage
   failure returns the existing safe invalid-media outcome and no usable reference.
5. When the outbound Message is created, its attachment is persisted as `AVAILABLE`
   with the returned stable key. A failed message transaction leaves the stored upload
   available for an explicit idempotent send retry.

### Inbound download

1. CRM-005 persists the inbound Message and attachment metadata as `PENDING` before
   external download/storage work.
2. Provider download and storage occur outside the database transaction.
3. Successful atomic storage is reconciled as `AVAILABLE`; a provider, validation, or
   storage failure is reconciled as `FAILED` with a safe error.
4. An explicit or authenticated lazy retry may move `FAILED` to `AVAILABLE`. Concurrent
   reconciliation must lock/recheck the attachment and never downgrade `AVAILABLE`.

No distributed transaction is assumed. If object storage succeeds but the final DB
update fails, the complete object may be orphaned and a retry remains safe; the Message
and attachment history stay intact. If the DB exists but storage fails, the attachment
remains `FAILED` and retryable. Partial objects are never treated as available.

## Security & permissions

- Filesystem roots and future buckets are private to the backend. Direct public access
  and public/signed object URLs are not client contracts.
- CRM-006 authentication remains mandatory for upload, preview, and attachment reads.
- Storage keys, filesystem paths, provider URLs, credentials, checksums, and private
  metadata are never returned to the frontend.
- The adapter accepts only its strict opaque-key grammar, resolves paths beneath the
  configured root, rejects traversal and symlink escapes, and never uses a supplied
  filename as a path.
- Responses use a validated `Content-Type`, sanitized RFC-compatible
  `Content-Disposition`, `nosniff`, and private/no-store caching as defined by CRM-006.
- Logs and metrics may include safe operation/result categories, never media bodies,
  filenames when avoidable, customer identifiers, paths, keys, or credentials.

## Edge cases

- Empty content, declared/detected MIME mismatch, unsupported content, and content over
  its type-specific limit are rejected before availability is recorded.
- Image and document maximum sizes and MIME allowlists are separate configuration
  values. Existing deployments may use the current common limit as a compatibility
  default, but no Meta/provider limit is hardcoded.
- V1 trusted inspection recognizes the actual signatures/structure of configured image
  formats and PDF. Filename extensions and client `Content-Type` alone are insufficient.
  An allowlisted format without a trusted inspector remains rejected.
- SHA-256 is calculated from stored bytes and verified on `get`; length and checksum
  mismatch is a safe corruption failure.
- Filenames are leaf names only, stripped of control characters and path components;
  absence of a filename remains valid.
- A retry using the same `media_ref` cannot replace different bytes. Independent
  duplicate uploads remain independent objects.
- Missing/corrupt content for a persisted attachment returns a safe unavailable-media
  response and reconciles storage evidence without deleting the Message.
- Complete orphan objects caused by a lost HTTP response or failed DB reconciliation
  are not deleted in the request path. Operational orphan cleanup requires a future
  retention spec.

## Acceptance criteria

- AC-01: `MediaStorage` exposes strictly typed `put`, `get`, and justified metadata
  lookup operations, with no cloud/provider types and no application-level `delete`.
- AC-02: `FakeMediaStorage` and the filesystem adapter round-trip validated IMAGE and
  PDF/DOCUMENT bytes plus private metadata through the same contract.
- AC-03: A new filesystem-adapter instance using the same configured root resolves the
  prior opaque `media_ref` and reads its content, demonstrating restart durability.
- AC-04: The filesystem adapter rejects malformed keys, traversal attempts, absolute
  paths, and symlink escapes, and no client response exposes its root, path, or key.
- AC-05: Writes use same-filesystem temporary objects and atomic promotion; injected
  failures leave no readable partial object and clean temporary artifacts.
- AC-06: Separate configurable image/document limits, MIME allowlists, detected content,
  nonempty content, and exact byte length are enforced for upload and inbound storage.
- AC-07: Stored bytes have a verified SHA-256 checksum; identical retry of one
  `media_ref` is idempotent and conflicting reuse fails without replacing content.
- AC-08: Outbound storage failure returns no usable `media_ref`, while successful upload
  remains resolvable for CRM-006 preview and subsequent fake-provider send.
- AC-09: Inbound failure records `FAILED`, retry can reach `AVAILABLE`, and concurrent or
  repeated retries neither downgrade availability nor corrupt attachment history.
- AC-10: Tests cover DB-before-storage and storage-before-DB failure boundaries without
  assuming a distributed transaction or exposing unsafe storage errors.
- AC-11: CRM-006 upload/content schemas, authenticated routes, `media_ref`, and no-base64
  behavior remain compatible; `FakeMediaStorage` remains usable in API/domain tests.
- AC-12: Docker development mounts the configured filesystem root from a named or bind
  volume, does not bake uploads into the image, and retains a test object across backend
  container recreation.
- AC-13: Customer or Opportunity soft deletion leaves attachment metadata and stored
  commercial-history media readable through authorized CRM APIs.

## Open decisions

None

## Follow-up / future specs

- Real S3-style object-storage adapter, deployment configuration, and credentials.
- Meta media upload/download integration.
- Legal retention, anonymization, orphan cleanup, and any approved deletion workflow.

## Implementation notes

The filesystem adapter reads its root from validated backend configuration (for example
`WHATSAPP_MEDIA_STORAGE_ROOT`) and stores one immutable object beneath that root. Docker
Compose mounts a named or explicit bind volume at the configured path; uploaded media
is never copied into the image layer.

Content and private metadata should be written into a temporary object beneath the same
root, flushed, and atomically renamed into place. Startup may remove only abandoned
temporary artifacts created by this adapter; that internal cleanup is not a historical
media delete operation.

A future S3-style adapter must preserve the same DTOs and semantics: private bucket and
prefix, atomic object PUT visibility, durable metadata lookup by `media_ref`, checksum
verification, idempotent conflicting-put behavior, normalized safe errors, and no
provider URLs. Domain services and CRM-006 routers must select adapters through
configuration and must not branch on filesystem versus object storage.
