# Data Model: File Upload to Azure Blob Storage with AI Processing

**Feature**: 008-blob-file-upload | **Date**: 2025-07-17

## Entities

### FileAttachment (Backend — Pydantic model in `app/src/models.py`)

Represents a user-uploaded file that has been stored in Azure Blob Storage.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `blob_name` | `str` | Required, max 255 chars | UUID-prefixed sanitized filename in blob storage |
| `original_filename` | `str` | Required, max 255 chars | Original filename as uploaded by user |
| `content_type` | `str` | Required, must be in ALLOWED_TYPES | MIME type of the file |
| `size_bytes` | `int` | Required, 1 ≤ n ≤ 10,485,760 | File size in bytes |

**Validation Rules**:
- `size_bytes` must be > 0 (reject empty files — edge case) and ≤ 10MB (10,485,760 bytes)
- `content_type` must be one of: `application/pdf`, `image/png`, `image/jpeg`, `image/gif`, `text/plain`, `text/csv`, `application/json`, `text/markdown`
- `blob_name` is generated server-side (not user-controlled)

---

### UploadResult (Backend — Pydantic model in `app/src/models.py`)

Response returned from the upload endpoint after successful blob storage.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `blob_name` | `str` | Required | Blob name in the storage container |
| `original_filename` | `str` | Required | Original filename for display |
| `content_type` | `str` | Required | MIME type |
| `size_bytes` | `int` | Required | File size in bytes |

---

### UploadErrorResponse (Backend — Pydantic model in `app/src/models.py`)

Error response for validation failures or upload errors.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `error` | `str` | Required | Error code (e.g., `FILE_TOO_LARGE`, `INVALID_TYPE`, `UPLOAD_FAILED`) |
| `detail` | `str` | Required | Human-readable error message |
| `max_size_bytes` | `int \| None` | Optional | Included when error is `FILE_TOO_LARGE` |
| `allowed_types` | `list[str] \| None` | Optional | Included when error is `INVALID_TYPE` |

---

### FileAttachment (Frontend — TypeScript interface in `app/frontend/src/types/file.ts`)

Frontend representation of a successfully uploaded file, returned from the upload endpoint.

```typescript
interface FileAttachment {
  blobName: string;
  originalFilename: string;
  contentType: string;
  sizeBytes: number;
}
```

---

### PendingFile (Frontend — TypeScript interface in `app/frontend/src/types/file.ts`)

Represents a file selected by the user but not yet uploaded.

```typescript
interface PendingFile {
  id: string;               // Client-generated UUID for tracking
  file: File;               // Browser File object
  status: 'pending' | 'uploading' | 'uploaded' | 'error';
  progress: number;         // 0-100 upload percentage
  error?: string;           // Error message if status is 'error'
  attachment?: FileAttachment; // Set when status is 'uploaded'
}
```

**State Transitions**:
```
pending → uploading → uploaded
                    → error
```

---

## Extended Entities (modifications to existing models)

### Message (Frontend — `app/frontend/src/types/message.ts`)

Add optional `attachments` field to existing `Message` interface:

```typescript
interface Message {
  // ... existing fields ...
  attachments?: FileAttachment[];  // NEW: file references for this message
}
```

### Chat/Teams request payloads

The existing `POST /` and `POST /v1/teams/stream` request bodies gain an optional `attachments` field:

```python
# In the raw JSON body parsed by routes.py:
{
  "messages": [...],
  "thread_id": "...",
  "attachments": [          # NEW: optional list of blob references
    {"blob_name": "...", "original_filename": "...", "content_type": "...", "size_bytes": ...}
  ]
}
```

---

## Constants (shared between validation layers)

### Backend (`app/src/file_validation.py`)

```python
MAX_FILE_SIZE_BYTES: int = 10_485_760  # 10 MB
MAX_FILES_PER_MESSAGE: int = 3
ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "text/plain",
    "text/csv",
    "application/json",
    "text/markdown",
}
ALLOWED_EXTENSIONS: set[str] = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".txt", ".csv", ".json", ".md",
}
MAX_FILENAME_LENGTH: int = 200
```

### Frontend (`app/frontend/src/types/file.ts`)

```typescript
const MAX_FILE_SIZE_BYTES = 10_485_760;  // 10 MB
const MAX_FILES_PER_MESSAGE = 3;
const ALLOWED_CONTENT_TYPES = [
  'application/pdf', 'image/png', 'image/jpeg', 'image/gif',
  'text/plain', 'text/csv', 'application/json', 'text/markdown',
];
const ALLOWED_EXTENSIONS = [
  '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.txt', '.csv', '.json', '.md',
];
```

---

## Blob Storage Layout

```
uploads/                          # Container (pre-provisioned)
├── {uuid}_{sanitized_filename}   # Individual blobs
├── {uuid}_{sanitized_filename}
└── ...
```

- Each blob is named `{uuid4}_{sanitized_filename}` to ensure uniqueness.
- No folder hierarchy — flat namespace within the `uploads` container.
- Content-Type metadata is set on the blob at upload time.
- No public access; all reads go through the authenticated backend.
