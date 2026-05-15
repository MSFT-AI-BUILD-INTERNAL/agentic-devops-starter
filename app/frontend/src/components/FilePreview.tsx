// FilePreview component for displaying pending file attachments
import type { PendingFile } from '../types/file';

interface FilePreviewProps {
  files: PendingFile[];
  onRemove: (id: string) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(contentType: string): string {
  if (contentType.startsWith('image/')) return '🖼️';
  if (contentType === 'application/pdf') return '📄';
  if (contentType === 'text/csv') return '📊';
  if (contentType === 'application/json') return '📋';
  return '📎';
}

export function FilePreview({ files, onRemove }: FilePreviewProps) {
  if (files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4 py-2">
      {files.map((file) => (
        <div
          key={file.id}
          className="flex items-center gap-2 bg-secondary border border-border rounded-lg px-3 py-2 text-sm max-w-[240px]"
        >
          <span className="text-base flex-shrink-0">{getFileIcon(file.file.type)}</span>
          <div className="flex-1 min-w-0">
            <div className="truncate text-text-primary text-xs font-medium">
              {file.file.name}
            </div>
            <div className="text-text-secondary text-xs">
              {formatFileSize(file.file.size)}
            </div>
            {file.status === 'uploading' && (
              <div className="w-full bg-border rounded-full h-1.5 mt-1">
                <div
                  className="bg-accent h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${file.progress}%` }}
                />
              </div>
            )}
            {file.status === 'error' && (
              <div className="text-red-500 text-xs truncate">{file.error}</div>
            )}
          </div>
          <div className="flex-shrink-0 flex items-center gap-1">
            {file.status === 'uploaded' && (
              <span className="text-green-500 text-sm">✓</span>
            )}
            {file.status === 'error' && (
              <span className="text-red-500 text-sm">✕</span>
            )}
            <button
              type="button"
              onClick={() => onRemove(file.id)}
              className="text-text-secondary hover:text-text-primary text-sm leading-none p-0.5"
              aria-label={`Remove ${file.file.name}`}
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
