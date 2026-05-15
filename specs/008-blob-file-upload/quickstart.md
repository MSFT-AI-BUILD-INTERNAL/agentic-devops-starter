# Quickstart: File Upload Feature Development

**Feature**: 008-blob-file-upload

## Prerequisites

- Python ≥3.12, Node.js ≥20, `uv` package manager
- Azure CLI logged in (`az login`) for local blob storage access via `DefaultAzureCredential`
- Access to the Azure Storage account (`stagenticdevops`) — your Azure identity needs Storage Blob Data Contributor role

## Environment Setup

### 1. Add Environment Variables

Add to `app/.env` (or export in your shell):

```bash
# Azure Blob Storage (required for file upload)
COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT=https://stagenticdevops.blob.core.windows.net/
COPILOT_API_AZURE_STORAGE_CONTAINER_NAME=uploads
```

### 2. Install Backend Dependencies

```bash
cd app
uv add azure-storage-blob azure-identity python-multipart
uv sync --frozen --all-extras
```

### 3. Install Frontend Dependencies

```bash
cd app/frontend
npm ci
```

## Running Locally

### Backend (terminal 1)

```bash
cd app
uv run agui_server.py
# → FastAPI server on http://localhost:5100
# → New endpoint: POST /v1/files/upload
```

### Frontend (terminal 2)

```bash
cd app/frontend
npm run dev
# → Vite dev server on http://localhost:8080
# → Proxies /api → localhost:5100
```

## Verification Steps

### 1. Upload a file

```bash
curl -X POST http://localhost:5100/v1/files/upload \
  -F "file=@test-file.txt" \
  -H "Content-Type: multipart/form-data"
```

Expected: `200 OK` with JSON containing `blob_name`, `original_filename`, `content_type`, `size_bytes`.

### 2. Verify validation (oversized file)

```bash
dd if=/dev/zero of=/tmp/big.bin bs=1M count=11
curl -X POST http://localhost:5100/v1/files/upload \
  -F "file=@/tmp/big.bin"
```

Expected: `413` with `FILE_TOO_LARGE` error.

### 3. Verify validation (invalid type)

```bash
curl -X POST http://localhost:5100/v1/files/upload \
  -F "file=@/usr/bin/ls;filename=test.exe;type=application/x-executable"
```

Expected: `415` with `INVALID_TYPE` error.

### 4. Send chat message with attachment

```bash
curl -X POST http://localhost:5100/ \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Summarize this file"}],
    "thread_id": "test-thread",
    "stream": true,
    "attachments": [{"blob_name": "<blob_name_from_step_1>", "original_filename": "test-file.txt", "content_type": "text/plain", "size_bytes": 100}]
  }'
```

Expected: SSE stream with AI response referencing the file content.

## Running Tests

```bash
# Backend
cd app
uv run pytest tests/ -v

# Frontend
cd app/frontend
npm run test
npm run lint
npm run type-check
```

## Key Files

| File | Purpose |
|------|---------|
| `app/src/blob_storage.py` | Azure Blob Storage upload/download service |
| `app/src/file_validation.py` | Shared file validation (type, size, filename) |
| `app/src/routes.py` | Upload endpoint + modified chat/teams endpoints |
| `app/src/models.py` | FileAttachment, UploadResult Pydantic models |
| `app/src/config.py` | Storage settings (endpoint, container name) |
| `app/frontend/src/hooks/useFileUpload.ts` | Upload hook with validation and progress |
| `app/frontend/src/services/fileUploadService.ts` | XHR upload client with progress events |
| `app/frontend/src/components/MessageInput.tsx` | Modified: 📎 button, drag-drop, previews |
| `app/frontend/src/components/FilePreview.tsx` | File preview with progress bar |
| `app/frontend/src/types/file.ts` | FileAttachment, PendingFile types + constants |
