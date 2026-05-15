# Implementation Plan: File Upload to Azure Blob Storage with AI Processing

**Branch**: `008-blob-file-upload` | **Date**: 2025-07-17 | **Spec**: `specs/008-blob-file-upload/spec.md`

**Input**: Feature specification from `specs/008-blob-file-upload/spec.md`

## Summary

Add file upload capability to both single-agent and team chat interfaces. Users attach files (PDF, images, text, CSV, JSON, Markdown) via a 📎 button or drag-and-drop. Files are validated client-side and server-side, uploaded to Azure Blob Storage via a new `POST /v1/files/upload` endpoint using managed identity, then downloaded by the backend and injected as context into the AI agent's prompt via the Copilot SDK. The frontend gains file attachment UI in `MessageInput.tsx`, upload progress tracking, and preview rendering. The backend gains a blob storage service, upload endpoint, and modified chat/teams endpoints that resolve file references before prompting.

## Technical Context

**Language/Version**: Python ≥3.12 (backend), TypeScript 5.3+ (frontend)

**Primary Dependencies**:
- Backend: FastAPI, Pydantic ≥2, `github-copilot-sdk`, `azure-storage-blob`, `azure-identity`, `python-multipart`
- Frontend: React 18.2, Zustand 5, Vite 7.3, Tailwind 3.4

**Storage**: Azure Blob Storage (account: `stagenticdevops`, container: `uploads`). Managed identity auth via `DefaultAzureCredential`. No shared keys or SAS tokens.

**Testing**: pytest + pytest-asyncio (backend), Vitest (frontend unit), Playwright (frontend E2E)

**Target Platform**: Linux server (Azure App Service) + modern web browsers

**Project Type**: Web application (FastAPI backend + React SPA frontend)

**Performance Goals**: File uploads ≤10s for files up to 5MB on standard broadband (SC-001)

**Constraints**: Max 10MB per file, max 3 files per message, allowed types: PDF, PNG, JPG/JPEG, GIF, TXT, CSV, JSON, MD

**Scale/Scope**: Single-user chat sessions, no concurrent multi-tenant file access concerns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First Backend | ✅ PASS | All backend code in Python ≥3.12 |
| II. Agent-Centric Architecture | ✅ PASS | File content injected into Copilot SDK agent prompt; no custom LLM logic |
| III. Type Safety | ✅ PASS | Pydantic models for all file/upload entities; mypy-compatible typing; strict TS frontend |
| IV. Response Quality | ✅ PASS | File content passed as context; AI model handles extraction; no custom parsing |
| V. Observability | ✅ PASS | Structured logging with correlation IDs for upload operations |
| VI. Project Structure | ✅ PASS | All app code in `app/`; no infra changes needed (storage already provisioned) |

**Gate result**: ✅ All gates pass. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/008-blob-file-upload/
├── plan.md              # This file
├── research.md          # Phase 0: research findings
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: dev setup guide
├── contracts/           # Phase 1: API contracts
│   ├── upload-endpoint.md
│   └── frontend-types.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
app/
├── src/
│   ├── config.py            # Add AZURE_STORAGE_* settings
│   ├── models.py            # Add FileAttachment, UploadResult, UploadRequest models
│   ├── routes.py            # Add POST /v1/files/upload; modify / and /v1/teams/stream
│   ├── blob_storage.py      # NEW: Azure Blob Storage service (upload, download)
│   └── file_validation.py   # NEW: Shared validation (type, size, filename sanitization)
├── tests/
│   ├── test_blob_storage.py # NEW: Unit tests for blob service
│   ├── test_file_upload.py  # NEW: Integration tests for upload endpoint
│   └── test_file_validation.py # NEW: Unit tests for validation
└── frontend/
    └── src/
        ├── components/
        │   ├── MessageInput.tsx    # Add file attachment UI (📎 button, drag-drop, previews)
        │   └── FilePreview.tsx     # NEW: File preview/thumbnail component
        ├── hooks/
        │   └── useFileUpload.ts    # NEW: Upload logic, progress tracking, validation
        ├── services/
        │   └── fileUploadService.ts # NEW: POST /v1/files/upload client
        ├── types/
        │   ├── message.ts          # Extend Message with optional attachments
        │   └── file.ts             # NEW: FileAttachment, UploadProgress types
        └── stores/
            └── chatStore.ts        # Add pending attachments state
```

**Structure Decision**: Web application pattern matching the existing `app/` layout. Backend additions are flat modules in `app/src/` (consistent with existing `routes.py`, `models.py`, `config.py`). Frontend additions follow existing `components/`, `hooks/`, `services/`, `types/` layout. No new directories at the repo root.

## Complexity Tracking

No constitution violations — table not needed.
