# Tasks: File Upload to Azure Blob Storage with AI Processing

**Input**: Design documents from `/specs/008-blob-file-upload/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and add configuration needed by all subsequent phases.

- [ ] T001 Add `azure-storage-blob`, `azure-identity`, and `python-multipart` to `app/pyproject.toml` dependencies and run `uv sync --frozen --all-extras`
- [ ] T002 Add `azure_storage_blob_endpoint` (str) and `azure_storage_container_name` (str, default `"uploads"`) settings to `Settings` class in `app/src/config.py`
- [ ] T003 [P] Add `COPILOT_API_AZURE_STORAGE_BLOB_ENDPOINT` and `COPILOT_API_AZURE_STORAGE_CONTAINER_NAME` entries to `app/.env` per `specs/008-blob-file-upload/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend modules that ALL user stories depend on — validation, blob storage service, Pydantic models. No user story can begin until these exist.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 [P] Create file validation module in `app/src/file_validation.py` with constants (`MAX_FILE_SIZE_BYTES`, `MAX_FILES_PER_MESSAGE`, `ALLOWED_CONTENT_TYPES`, `ALLOWED_EXTENSIONS`, `MAX_FILENAME_LENGTH`) and functions: `validate_file_type(content_type: str, filename: str) -> None`, `validate_file_size(size: int) -> None`, `sanitize_filename(filename: str) -> str` (strip non-ASCII, collapse whitespace, truncate to 200 chars). Raise `ValueError` with descriptive messages on failure. See `specs/008-blob-file-upload/data-model.md` for exact values.
- [ ] T005 [P] Add Pydantic models `FileAttachment`, `UploadResult`, and `UploadErrorResponse` to `app/src/models.py` per field definitions in `specs/008-blob-file-upload/data-model.md`. Add optional `attachments: list[FileAttachment] | None = None` field to `TeamsRequest` model in the same file.
- [ ] T006 Create blob storage service in `app/src/blob_storage.py`: class `BlobStorageService` with `__init__(self, settings: Settings)` that creates a `BlobServiceClient` using `DefaultAzureCredential`, method `async upload(file_content: bytes, blob_name: str, content_type: str) -> str` to upload to the configured container, and method `async download(blob_name: str) -> bytes` to download blob content. Use the `azure_storage_blob_endpoint` and `azure_storage_container_name` from settings. Instantiate once at module level. See research decision R-001 in `specs/008-blob-file-upload/research.md`.
- [ ] T007 [P] Create frontend file types in `app/frontend/src/types/file.ts`: export `FileAttachment` interface, `PendingFile` interface, `UploadError` interface, and `FILE_UPLOAD_LIMITS` const object exactly as defined in `specs/008-blob-file-upload/contracts/frontend-types.md`
- [ ] T008 [P] Add optional `attachments?: FileAttachment[]` field to the `Message` interface in `app/frontend/src/types/message.ts` and add the `FileAttachment` import from `./file`

**Checkpoint**: Foundation ready — upload endpoint, frontend types, and blob service in place for user story implementation.

---

## Phase 3: User Story 1 — Upload a File and Get AI Analysis (Priority: P1) 🎯 MVP

**Goal**: A user attaches a file (📎 or drag-and-drop) in single-agent chat, sees a preview, sends the message, and the AI agent responds with analysis of the file content.

**Independent Test**: Attach a single PDF in single-agent chat → verify AI response references file content.

### Implementation for User Story 1

- [ ] T009 [US1] Add `POST /v1/files/upload` endpoint to `app/src/routes.py`: accept `file: UploadFile`, validate with `file_validation.validate_file_type()` and `validate_file_size()`, sanitize filename, generate UUID-prefixed blob name, upload via `BlobStorageService.upload()`, return `UploadResult` JSON. Return `413`/`415`/`422`/`502` error responses per `specs/008-blob-file-upload/contracts/upload-endpoint.md`.
- [ ] T010 [US1] Create helper function `_resolve_attachments(attachments: list[FileAttachment]) -> str` in `app/src/routes.py` that downloads each blob via `BlobStorageService.download()`, formats text files as `[File: {filename}]\n{content}\n\n` and binary files as base64 with MIME metadata, and returns the combined context string. See research decision R-003 in `specs/008-blob-file-upload/research.md`.
- [ ] T011 [US1] Modify `_build_prompt()` in `app/src/routes.py` to accept an optional `attachments: list[dict] | None` parameter; when present, call `_resolve_attachments()` and prepend the file context to the extracted user message.
- [ ] T012 [US1] Modify `agent_endpoint()` in `app/src/routes.py` to extract optional `attachments` list from `input_data` and pass it to `_build_prompt()` so file content is injected into the Copilot SDK prompt.
- [ ] T013 [P] [US1] Create file upload service in `app/frontend/src/services/fileUploadService.ts`: export `uploadFile(file: File, onProgress?: (percent: number) => void): Promise<FileAttachment>` using `XMLHttpRequest` with `upload.onprogress` for progress tracking. POST to `/api/v1/files/upload` as multipart/form-data. Parse JSON response as `FileAttachment`. Throw on error responses. See research decision R-006 in `specs/008-blob-file-upload/research.md`.
- [ ] T014 [P] [US1] Create `useFileUpload` hook in `app/frontend/src/hooks/useFileUpload.ts` implementing the `UseFileUploadReturn` interface from `specs/008-blob-file-upload/contracts/frontend-types.md`: manage `pendingFiles` state array, `addFiles()` with client-side validation (type, size, count against `FILE_UPLOAD_LIMITS`), `removeFile()`, `uploadAll()` calling `fileUploadService.uploadFile()` for each pending file, `clearFiles()`, computed `isUploading`, `isAtLimit`, and `validationError`.
- [ ] T015 [P] [US1] Create `FilePreview` component in `app/frontend/src/components/FilePreview.tsx`: display each `PendingFile` with filename, file size (human-readable), file type icon, upload progress bar (when status is `uploading`), success indicator (when `uploaded`), error message (when `error`), and a remove button (✕) that calls `removeFile(id)`.
- [ ] T016 [US1] Modify `MessageInput` component in `app/frontend/src/components/MessageInput.tsx`: add a hidden `<input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.gif,.txt,.csv,.json,.md">` triggered by a 📎 button, integrate `useFileUpload` hook, render `FilePreview` for each pending file below the textarea, add drag-and-drop handlers (`onDragOver`, `onDragLeave`, `onDrop`) on the form container, update `onSendMessage` prop signature to `(message: string, attachments?: FileAttachment[]) => void`, call `uploadAll()` before sending and include returned attachments.
- [ ] T017 [US1] Update `useChat` hook in `app/frontend/src/hooks/useChat.ts` to accept optional `attachments: FileAttachment[]` in the send message flow, include `attachments` field in the JSON body posted to the AG-UI agent endpoint (`POST /`).
- [ ] T018 [US1] Update `chatStore` in `app/frontend/src/stores/chatStore.ts`: when `addMessage` is called for a user message with attachments, store the `attachments` array on the `Message` object.

**Checkpoint**: At this point, a user can attach a file in single-agent chat, upload it, and receive an AI response that references the file content. User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 — Upload Files in Team Chat (Priority: P2)

**Goal**: A user attaches up to 3 files in team chat and all agents in the team can access the file content for their responses.

**Independent Test**: Attach files in a team chat session → verify team agent responses reference the attached file content.

### Implementation for User Story 2

- [ ] T019 [US2] Modify `teams_stream()` endpoint in `app/src/routes.py` to extract optional `attachments` from `request`, call `_resolve_attachments()` to build file context string, and prepend it to `request.prompt` before passing to `run_teams()`.
- [ ] T020 [US2] Update `useTeams` hook in `app/frontend/src/hooks/useTeams.ts` to accept optional `attachments: FileAttachment[]` in the send/run flow and include `attachments` field in the JSON body posted to `POST /v1/teams/stream`.
- [ ] T021 [US2] Update `teamsStore` in `app/frontend/src/stores/teamsStore.ts` to store attachments on messages when provided.

**Checkpoint**: At this point, file upload works in both single-agent chat and team chat. User Stories 1 AND 2 are independently functional.

---

## Phase 5: User Story 3 — Upload Validation and Error Feedback (Priority: P2)

**Goal**: Users receive clear, immediate feedback when attempting to upload invalid files (wrong type, oversized, too many files, empty files).

**Independent Test**: Attempt to attach files of various invalid types and sizes → verify rejection messages appear without any upload attempt.

### Implementation for User Story 3

- [ ] T022 [US3] Add client-side validation error display in `useFileUpload` hook in `app/frontend/src/hooks/useFileUpload.ts`: in `addFiles()`, set `validationError` state with specific messages for file too large ("File exceeds 10MB limit"), unsupported type ("Supported types: PDF, PNG, JPG, GIF, TXT, CSV, JSON, MD"), max count reached ("Maximum of 3 files per message"), and empty file ("File is empty"). Clear error after 5 seconds or on next valid action.
- [ ] T023 [US3] Add validation error banner to `MessageInput` in `app/frontend/src/components/MessageInput.tsx`: render `validationError` from `useFileUpload` as a dismissible error alert above the file preview area with red styling and the list of supported types when relevant.
- [ ] T024 [P] [US3] Add server-side validation for empty files (0 bytes) in the upload endpoint in `app/src/routes.py`: check `file.size` and return `422` with `EMPTY_FILE` error response per `specs/008-blob-file-upload/contracts/upload-endpoint.md`.
- [ ] T025 [US3] Handle upload error responses in `fileUploadService.ts` in `app/frontend/src/services/fileUploadService.ts`: parse `UploadError` JSON from 4xx/5xx responses and propagate structured error to the `useFileUpload` hook so it can display server-side rejection messages.

**Checkpoint**: All validation paths have clear user feedback. User Story 3 is independently testable.

---

## Phase 6: User Story 4 — Upload Progress Visibility (Priority: P3)

**Goal**: Users see real-time upload progress for each file, with a progress bar during upload and a success/failure indicator on completion.

**Independent Test**: Upload a large file (close to 10MB) → verify progress indicator appears and transitions to success state.

### Implementation for User Story 4

- [ ] T026 [US4] Enhance `FilePreview` component in `app/frontend/src/components/FilePreview.tsx`: add an animated progress bar (0–100%) driven by `PendingFile.progress`, smooth CSS transition on width changes, show percentage text, transition to green checkmark on `uploaded` status, show red error icon on `error` status.
- [ ] T027 [US4] Add upload state styling to `MessageInput` in `app/frontend/src/components/MessageInput.tsx`: disable the Send button while `isUploading` is true, show "Uploading..." text on the Send button during upload, re-enable after all uploads complete or fail.

**Checkpoint**: All four user stories are complete and independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge case hardening, logging, and final validation across all stories.

- [ ] T028 [P] Add structured logging with correlation IDs to `app/src/blob_storage.py` and the upload endpoint in `app/src/routes.py`: log upload start, completion (with blob name and size), and failures using `setup_logging()` from `src/logging_utils`
- [ ] T029 [P] Add filename sanitization edge-case handling in `app/src/file_validation.py`: handle filenames >255 chars (truncate), filenames with unicode/special characters (strip unsafe chars, preserve readability), and filenames with path traversal attempts (strip directory components)
- [ ] T030 Add drag-and-drop visual feedback to `MessageInput` in `app/frontend/src/components/MessageInput.tsx`: show a dashed border highlight and "Drop files here" overlay text when files are dragged over the chat area, remove on drag leave or drop
- [ ] T031 Run quickstart.md validation steps from `specs/008-blob-file-upload/quickstart.md`: verify `POST /v1/files/upload` returns 200 with valid file, 413 for oversized file, 415 for invalid type, and chat endpoint with attachments returns AI response referencing file content

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) — the MVP
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2); reuses `_resolve_attachments()` from US1
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2); refines validation from US1
- **User Story 4 (Phase 6)**: Depends on US1 (FilePreview exists from T015)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **User Story 2 (P2)**: Shares `_resolve_attachments()` from US1 — best done after US1 but only T010 is a true blocker
- **User Story 3 (P2)**: Refines validation already scaffolded in US1 — can start after Phase 2 but benefits from US1
- **User Story 4 (P3)**: Enhances `FilePreview` from T015 — requires US1 to be complete

### Within Each User Story

- Backend models/services before endpoints
- Endpoints before frontend integration
- Frontend types → service → hook → component (dependency chain)
- Core implementation before polish/edge cases

### Parallel Opportunities

- T004, T005, T007, T008 can all run in parallel (different files, no dependencies)
- T013, T014, T015 can run in parallel (different frontend files, all depend only on T007)
- T019 (backend) and T020/T021 (frontend) within US2 are independent
- T022 and T024 are on different files (frontend hook vs backend route)
- T028 and T029 are independent polish tasks on different files

---

## Parallel Example: Phase 2 (Foundational)

```bash
# All these tasks touch different files — launch together:
Task T004: "Create file validation module in app/src/file_validation.py"
Task T005: "Add Pydantic models to app/src/models.py"
Task T007: "Create frontend file types in app/frontend/src/types/file.ts"
Task T008: "Add attachments field to Message in app/frontend/src/types/message.ts"
```

## Parallel Example: User Story 1 (Frontend)

```bash
# After T007 (frontend types) is complete, launch these together:
Task T013: "Create file upload service in app/frontend/src/services/fileUploadService.ts"
Task T014: "Create useFileUpload hook in app/frontend/src/hooks/useFileUpload.ts"
Task T015: "Create FilePreview component in app/frontend/src/components/FilePreview.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T008)
3. Complete Phase 3: User Story 1 (T009–T018)
4. **STOP and VALIDATE**: Test by uploading a PDF in single-agent chat, verify AI references its content
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (**MVP!**)
3. Add User Story 2 → Test team chat independently → Deploy/Demo
4. Add User Story 3 → Test validation edge cases → Deploy/Demo
5. Add User Story 4 → Test progress UX → Deploy/Demo
6. Polish → Final validation → Ship

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (backend T009–T012, then frontend T013–T018)
   - Developer B: User Story 3 server-side validation (T024) in parallel with Developer A
3. After US1 merges: US2 and US4 can proceed in parallel
