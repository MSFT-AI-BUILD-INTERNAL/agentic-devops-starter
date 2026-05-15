# Frontend Type Contracts: File Upload

**Feature**: 008-blob-file-upload

## New Types (`app/frontend/src/types/file.ts`)

```typescript
/** Successfully uploaded file reference (mirrors backend UploadResult) */
export interface FileAttachment {
  blobName: string;
  originalFilename: string;
  contentType: string;
  sizeBytes: number;
}

/** Client-side file tracking before/during/after upload */
export interface PendingFile {
  id: string;                        // crypto.randomUUID()
  file: File;                        // Browser File object
  status: 'pending' | 'uploading' | 'uploaded' | 'error';
  progress: number;                  // 0–100
  error?: string;                    // Present when status === 'error'
  attachment?: FileAttachment;       // Present when status === 'uploaded'
}

/** Validation constraints (must match backend) */
export const FILE_UPLOAD_LIMITS = {
  MAX_FILE_SIZE_BYTES: 10_485_760,   // 10 MB
  MAX_FILES_PER_MESSAGE: 3,
  ALLOWED_CONTENT_TYPES: [
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/gif',
    'text/plain',
    'text/csv',
    'application/json',
    'text/markdown',
  ] as const,
  ALLOWED_EXTENSIONS: [
    '.pdf', '.png', '.jpg', '.jpeg', '.gif',
    '.txt', '.csv', '.json', '.md',
  ] as const,
} as const;

/** Upload error from the server */
export interface UploadError {
  error: string;
  detail: string;
  maxSizeBytes?: number;
  allowedTypes?: string[];
}
```

## Extended Types

### Message (`app/frontend/src/types/message.ts`)

```typescript
export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  threadId: string;
  toolCalls?: import('./agui').ToolCall[];
  metadata?: MessageMetadata;
  attachments?: FileAttachment[];    // NEW
}
```

## Hook Contract (`app/frontend/src/hooks/useFileUpload.ts`)

```typescript
interface UseFileUploadReturn {
  /** Currently selected/uploading files */
  pendingFiles: PendingFile[];

  /** Add files from input or drag-drop (validates before adding) */
  addFiles: (files: FileList | File[]) => void;

  /** Remove a pending file by ID */
  removeFile: (id: string) => void;

  /** Upload all pending files, returns attachments for successfully uploaded ones */
  uploadAll: () => Promise<FileAttachment[]>;

  /** Clear all pending files */
  clearFiles: () => void;

  /** Whether any upload is in progress */
  isUploading: boolean;

  /** Whether the max file count has been reached */
  isAtLimit: boolean;

  /** Last validation error (e.g., "File exceeds 10MB limit") */
  validationError: string | null;
}
```

## Service Contract (`app/frontend/src/services/fileUploadService.ts`)

```typescript
/** Upload a single file to the backend. Uses XHR for progress tracking. */
export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<FileAttachment>;
```
