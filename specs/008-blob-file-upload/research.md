# Research: File Upload to Azure Blob Storage with AI Processing

**Feature**: 008-blob-file-upload | **Date**: 2025-07-17

## R-001: Azure Blob Storage SDK Authentication with Managed Identity

**Decision**: Use `azure-storage-blob` with `DefaultAzureCredential` from `azure-identity` for all blob operations.

**Rationale**: The spec mandates managed identity (FR-010: no shared keys or SAS tokens). `DefaultAzureCredential` automatically uses the App Service's system-assigned managed identity in production and falls back to Azure CLI credentials in local development, requiring zero code changes between environments. The storage account Terraform module already outputs `primary_blob_endpoint`, and the App Service already has Storage Blob Data Contributor role assigned.

**Alternatives Considered**:
- **SAS tokens**: Rejected — spec explicitly prohibits (FR-010). Also adds token management complexity and expiration handling.
- **Shared access keys**: Rejected — spec explicitly prohibits (FR-010). Security anti-pattern for production workloads.
- **Pre-signed upload URLs (client-direct)**: Rejected — would require SAS token generation, violates FR-010, and bypasses server-side validation (FR-008).

**Implementation Notes**:
- Use `BlobServiceClient(account_url=endpoint, credential=DefaultAzureCredential())` — instantiate once at startup, reuse.
- Env vars: `AZURE_STORAGE_BLOB_ENDPOINT` (blob endpoint URL), `AZURE_STORAGE_CONTAINER_NAME` (default: `uploads`).
- Add both to `Settings` in `config.py` with the existing `COPILOT_API_` prefix.

---

## R-002: FastAPI File Upload with python-multipart

**Decision**: Use `UploadFile` from FastAPI with `python-multipart` for the upload endpoint.

**Rationale**: FastAPI's `UploadFile` uses `python-multipart` under the hood to parse multipart/form-data. It streams file content without loading entire files into memory, which is important for the 10MB limit. The `UploadFile` object provides `.filename`, `.content_type`, `.size`, and an async `.read()` method — everything needed for validation and forwarding to blob storage.

**Alternatives Considered**:
- **Base64 in JSON body**: Rejected — 33% overhead on file size, no streaming, poor memory characteristics for 10MB files.
- **Custom multipart parsing**: Rejected — unnecessary; FastAPI handles this natively.

**Implementation Notes**:
- Endpoint: `POST /v1/files/upload` accepting `file: UploadFile` (single file per request; frontend sends multiple requests for multi-file).
- Server-side validation before blob upload: check file size, MIME type, filename length.
- Return `UploadResult` with blob name and URL reference.

---

## R-003: File Content Injection into Copilot SDK Prompts

**Decision**: Download blob content on the backend and prepend it to the user's message as structured context before sending to the Copilot SDK session.

**Rationale**: The Copilot SDK's `CopilotSession.send()` accepts a text prompt. Since the AI model handles content extraction (spec assumption), we pass raw text content for text-based files and base64-encoded content for binary files (images, PDFs) with MIME type metadata. The model (GPT-4o, etc.) natively supports image and document understanding.

**Alternatives Considered**:
- **Custom PDF/image extraction**: Rejected — spec explicitly states file content extraction is handled by the AI model, not custom code.
- **Passing blob URLs to the model**: Rejected — model cannot access Azure Blob Storage directly; backend must mediate (FR-016).
- **Storing extracted text alongside blob**: Rejected — adds complexity; model handles extraction.

**Implementation Notes**:
- For text-based files (TXT, CSV, JSON, MD): read as UTF-8 text, prepend as `[File: {filename}]\n{content}\n\n`.
- For binary files (PDF, PNG, JPG, GIF): read as bytes, base64-encode, include MIME type for model multimodal input.
- Download from blob at chat-time, not at upload-time (keeps upload fast).
- Modify `_build_prompt()` in `routes.py` to accept and format file references.

---

## R-004: Frontend File Upload UX Pattern

**Decision**: Add file attachment to `MessageInput.tsx` with a hidden `<input type="file">` triggered by a 📎 button, plus drag-and-drop on the chat area. Upload files via `POST /v1/files/upload` before sending the chat message.

**Rationale**: This is the standard web file upload pattern. The upload happens as a separate HTTP request before the chat message is sent, so the chat SSE stream doesn't need to handle multipart data. The frontend collects blob references from upload responses and includes them in the chat message payload.

**Alternatives Considered**:
- **Upload embedded in SSE stream**: Rejected — SSE is server-to-client; mixing multipart upload into the chat request would break the AG-UI protocol.
- **Drag-and-drop only (no button)**: Rejected — spec requires both (FR-001 + FR-002); button is more discoverable.
- **Upload on message send (synchronous)**: Considered but rejected as primary pattern — uploading before send allows progress indication and validation feedback before committing to the message.

**Implementation Notes**:
- New `useFileUpload` hook: manages pending files, validation, upload progress, and blob references.
- New `FilePreview` component: shows filename, size, type icon, and remove button for each pending attachment.
- `MessageInput.tsx` gains file attachment state and passes blob references with the message.
- Chat store and teams store extend message payloads to include `attachments: FileAttachment[]`.

---

## R-005: Client-Side File Validation Strategy

**Decision**: Validate file type, size, and count on the client before upload. Duplicate validation on the server as defense-in-depth (FR-008).

**Rationale**: Client-side validation provides instant feedback (no network round-trip). Server-side validation is mandatory for security (clients can be bypassed). Both layers use the same constraints: 10MB max size, allowed MIME types, 3-file max per message.

**Alternatives Considered**:
- **Server-only validation**: Rejected — poor UX; user waits for upload to fail. Also wastes bandwidth.
- **Client-only validation**: Rejected — insecure; clients can be modified.

**Implementation Notes**:
- Allowed types constant shared between frontend and backend:
  - MIME: `application/pdf`, `image/png`, `image/jpeg`, `image/gif`, `text/plain`, `text/csv`, `application/json`, `text/markdown`
  - Extensions: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.txt`, `.csv`, `.json`, `.md`
- Filename sanitization: strip non-ASCII, collapse whitespace, truncate to 200 chars, prepend UUID prefix for uniqueness.

---

## R-006: Upload Progress Tracking via XMLHttpRequest

**Decision**: Use `XMLHttpRequest` with `upload.onprogress` events for upload progress tracking, wrapped in the `fileUploadService.ts`.

**Rationale**: The Fetch API does not support upload progress events. `XMLHttpRequest` is the only browser API that exposes `progress` events with `loaded`/`total` bytes during upload. Since progress visibility is a P3 requirement (FR-004), this is the appropriate mechanism.

**Alternatives Considered**:
- **Fetch API**: Rejected — no upload progress events. Would have to show indeterminate spinner only.
- **Chunked upload with progress**: Rejected — over-engineering for 10MB max files. Azure Blob SDK handles large uploads internally.
- **Server-Sent Events for progress**: Rejected — would require a separate SSE connection per upload; the server already streams to blob synchronously.

**Implementation Notes**:
- `fileUploadService.ts` exports `uploadFile(file: File, onProgress: (pct: number) => void): Promise<UploadResult>`.
- Progress state stored in `useFileUpload` hook per file.
- `FilePreview` component renders a progress bar when upload is in flight.
