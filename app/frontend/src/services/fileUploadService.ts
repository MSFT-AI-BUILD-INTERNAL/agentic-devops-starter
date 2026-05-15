// File upload service using XMLHttpRequest for progress tracking
import { getApiBaseUrl } from '../config/api';
import type { FileAttachment, UploadError } from '../types/file';

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<FileAttachment> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          const attachment: FileAttachment = {
            blobName: data.blob_name,
            originalFilename: data.original_filename,
            contentType: data.content_type,
            sizeBytes: data.size_bytes,
          };
          resolve(attachment);
        } catch {
          reject(new Error('Failed to parse upload response'));
        }
      } else {
        try {
          const error: UploadError = JSON.parse(xhr.responseText);
          reject(new Error(error.detail || error.error));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Network error during upload'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload was cancelled'));
    });

    const baseUrl = getApiBaseUrl();
    xhr.open('POST', `${baseUrl}/v1/files/upload`);
    xhr.send(formData);
  });
}
