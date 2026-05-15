// useFileUpload hook for managing file attachment lifecycle
import { useState, useCallback } from 'react';
import { uploadFile } from '../services/fileUploadService';
import { generateUUID } from '../utils/uuid';
import type { FileAttachment, PendingFile } from '../types/file';
import { FILE_UPLOAD_LIMITS } from '../types/file';

export interface UseFileUploadReturn {
  pendingFiles: PendingFile[];
  addFiles: (files: FileList | File[]) => void;
  removeFile: (id: string) => void;
  uploadAll: () => Promise<FileAttachment[]>;
  clearFiles: () => void;
  isUploading: boolean;
  isAtLimit: boolean;
  validationError: string | null;
}

export function useFileUpload(): UseFileUploadReturn {
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const clearValidationError = useCallback(() => {
    setTimeout(() => setValidationError(null), 5000);
  }, []);

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const fileArray = Array.from(files);

      for (const file of fileArray) {
        // Check count limit
        if (pendingFiles.length + fileArray.indexOf(file) >= FILE_UPLOAD_LIMITS.maxFilesPerMessage) {
          setValidationError(
            `Maximum of ${FILE_UPLOAD_LIMITS.maxFilesPerMessage} files per message`
          );
          clearValidationError();
          return;
        }

        // Check size
        if (file.size > FILE_UPLOAD_LIMITS.maxFileSizeBytes) {
          setValidationError('File exceeds 10MB limit');
          clearValidationError();
          return;
        }

        // Check empty
        if (file.size === 0) {
          setValidationError('File is empty');
          clearValidationError();
          return;
        }

        // Check type
        const ext = '.' + (file.name.split('.').pop()?.toLowerCase() || '');
        const typeAllowed =
          FILE_UPLOAD_LIMITS.allowedContentTypes.includes(file.type as typeof FILE_UPLOAD_LIMITS.allowedContentTypes[number]) ||
          FILE_UPLOAD_LIMITS.allowedExtensions.includes(ext as typeof FILE_UPLOAD_LIMITS.allowedExtensions[number]);
        if (!typeAllowed) {
          setValidationError(
            'Supported types: PDF, PNG, JPG, GIF, TXT, CSV, JSON, MD'
          );
          clearValidationError();
          return;
        }
      }

      setValidationError(null);
      const newPending: PendingFile[] = fileArray.map((file) => ({
        id: generateUUID(),
        file,
        status: 'pending' as const,
        progress: 0,
      }));

      setPendingFiles((prev) => [...prev, ...newPending]);
    },
    [pendingFiles.length, clearValidationError]
  );

  const removeFile = useCallback((id: string) => {
    setPendingFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const uploadAll = useCallback(async (): Promise<FileAttachment[]> => {
    setIsUploading(true);
    const results: FileAttachment[] = [];

    try {
      for (const pending of pendingFiles) {
        if (pending.status === 'uploaded' && pending.attachment) {
          results.push(pending.attachment);
          continue;
        }

        setPendingFiles((prev) =>
          prev.map((f) => (f.id === pending.id ? { ...f, status: 'uploading' as const } : f))
        );

        try {
          const attachment = await uploadFile(pending.file, (percent) => {
            setPendingFiles((prev) =>
              prev.map((f) => (f.id === pending.id ? { ...f, progress: percent } : f))
            );
          });

          setPendingFiles((prev) =>
            prev.map((f) =>
              f.id === pending.id
                ? { ...f, status: 'uploaded' as const, progress: 100, attachment }
                : f
            )
          );
          results.push(attachment);
        } catch (error) {
          const errMsg = error instanceof Error ? error.message : 'Upload failed';
          setPendingFiles((prev) =>
            prev.map((f) =>
              f.id === pending.id ? { ...f, status: 'error' as const, error: errMsg } : f
            )
          );
        }
      }
    } finally {
      setIsUploading(false);
    }

    return results;
  }, [pendingFiles]);

  const clearFiles = useCallback(() => {
    setPendingFiles([]);
    setValidationError(null);
  }, []);

  const isAtLimit = pendingFiles.length >= FILE_UPLOAD_LIMITS.maxFilesPerMessage;

  return {
    pendingFiles,
    addFiles,
    removeFile,
    uploadAll,
    clearFiles,
    isUploading,
    isAtLimit,
    validationError,
  };
}
