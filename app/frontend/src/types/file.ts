// File upload types and constants

export interface FileAttachment {
  blobName: string;
  originalFilename: string;
  contentType: string;
  sizeBytes: number;
}

export interface PendingFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'uploaded' | 'error';
  progress: number;
  error?: string;
  attachment?: FileAttachment;
}

export interface UploadError {
  error: string;
  detail: string;
  maxSizeBytes?: number;
  allowedTypes?: string[];
}

export const FILE_UPLOAD_LIMITS = {
  maxFileSizeBytes: 10_485_760, // 10 MB
  maxFilesPerMessage: 3,
  allowedContentTypes: [
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/gif',
    'text/plain',
    'text/csv',
    'application/json',
    'text/markdown',
  ],
  allowedExtensions: [
    '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.txt', '.csv', '.json', '.md',
  ],
} as const;
