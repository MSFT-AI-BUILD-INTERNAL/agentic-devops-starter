# API Contract: File Upload Endpoint

**Feature**: 008-blob-file-upload | **Endpoint**: `POST /v1/files/upload`

## Upload File

Uploads a single file to Azure Blob Storage. Called once per file; for multi-file messages, the client sends multiple requests.

### Request

```
POST /v1/files/upload
Content-Type: multipart/form-data
```

| Part | Type | Required | Constraints |
|------|------|----------|-------------|
| `file` | binary (multipart) | Yes | Max 10MB, allowed types only |

### Success Response

```
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "blob_name": "a1b2c3d4-5678-9abc-def0-123456789abc_report.pdf",
  "original_filename": "report.pdf",
  "content_type": "application/pdf",
  "size_bytes": 245760
}
```

### Error Responses

#### 413 — File Too Large

```json
{
  "error": "FILE_TOO_LARGE",
  "detail": "File size 15728640 bytes exceeds maximum of 10485760 bytes (10MB)",
  "max_size_bytes": 10485760,
  "allowed_types": null
}
```

#### 415 — Unsupported File Type

```json
{
  "error": "INVALID_TYPE",
  "detail": "File type application/x-executable is not allowed",
  "max_size_bytes": null,
  "allowed_types": ["application/pdf", "image/png", "image/jpeg", "image/gif", "text/plain", "text/csv", "application/json", "text/markdown"]
}
```

#### 422 — Empty File

```json
{
  "error": "EMPTY_FILE",
  "detail": "File is empty (0 bytes)",
  "max_size_bytes": null,
  "allowed_types": null
}
```

#### 502 — Storage Unavailable

```json
{
  "error": "UPLOAD_FAILED",
  "detail": "Failed to upload file to storage. Please try again.",
  "max_size_bytes": null,
  "allowed_types": null
}
```

---

## Modified Chat Endpoint

### `POST /` (AG-UI single-agent chat)

The existing endpoint's JSON body gains an optional `attachments` field:

```json
{
  "messages": [
    {"role": "user", "content": "Analyze this report"}
  ],
  "thread_id": "thread-abc-123",
  "stream": true,
  "attachments": [
    {
      "blob_name": "a1b2c3d4_report.pdf",
      "original_filename": "report.pdf",
      "content_type": "application/pdf",
      "size_bytes": 245760
    }
  ]
}
```

**Behavior change**: When `attachments` is present and non-empty, the backend downloads each blob, formats file content, and prepends it to the prompt before sending to the Copilot SDK session.

SSE events remain unchanged. No new event types.

---

## Modified Teams Endpoint

### `POST /v1/teams/stream`

The existing `TeamsRequest` model gains an optional `attachments` field:

```json
{
  "pattern_id": "debate",
  "prompt": "Review this data",
  "max_rounds": 3,
  "thread_id": "team-thread-456",
  "attachments": [
    {
      "blob_name": "b2c3d4e5_data.csv",
      "original_filename": "data.csv",
      "content_type": "text/csv",
      "size_bytes": 1024
    }
  ]
}
```

**Behavior change**: Identical to single-agent — file content is prepended to the prompt before execution.
