// MessageInput component with keyboard submission and file attachment
import { useState, useCallback, KeyboardEvent, FormEvent, useRef, DragEvent } from 'react';
import { logger } from '../utils/logger';
import { useFileUpload } from '../hooks/useFileUpload';
import { FilePreview } from './FilePreview';
import type { FileAttachment } from '../types/file';

const ACCEPTED_FILE_TYPES = '.pdf,.png,.jpg,.jpeg,.gif,.txt,.csv,.json,.md';

interface MessageInputProps {
  onSendMessage: (message: string, attachments?: FileAttachment[]) => void;
  onStopGenerating?: () => void | Promise<void>;
  disabled?: boolean;
  isGenerating?: boolean;
  placeholder?: string;
}

export function MessageInput({
  onSendMessage,
  onStopGenerating,
  disabled = false,
  isGenerating = false,
  placeholder = 'Type your message...',
}: MessageInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    pendingFiles,
    addFiles,
    removeFile,
    uploadAll,
    clearFiles,
    isUploading,
    isAtLimit,
    validationError,
  } = useFileUpload();

  /**
   * Auto-resize textarea based on content
   */
  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, []);

  /**
   * Handle message submission
   */
  const handleSubmit = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();

      const message = inputValue.trim();

      if ((!message && pendingFiles.length === 0) || disabled || isSubmitting || isUploading) {
        return;
      }

      logger.debug('Submitting message', { length: message.length, files: pendingFiles.length });

      setIsSubmitting(true);

      try {
        let attachments: FileAttachment[] | undefined;

        if (pendingFiles.length > 0) {
          attachments = await uploadAll();
          if (attachments.length === 0) {
            // All uploads failed
            return;
          }
        }

        await onSendMessage(message, attachments);
        setInputValue('');
        clearFiles();
        if (textareaRef.current) {
          textareaRef.current.style.height = 'auto';
        }
      } catch (error) {
        logger.error('Failed to send message', error);
      } finally {
        setIsSubmitting(false);
      }
    },
    [inputValue, pendingFiles, disabled, isSubmitting, isUploading, onSendMessage, uploadAll, clearFiles]
  );

  const handleStopGenerating = useCallback(async () => {
    if (!onStopGenerating || isStopping) {
      return;
    }

    setIsStopping(true);
    try {
      await onStopGenerating();
    } catch (error) {
      logger.error('Failed to stop generation', error);
    } finally {
      setIsStopping(false);
    }
  }, [onStopGenerating, isStopping]);

  /**
   * Handle keyboard shortcuts
   */
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  /**
   * Handle input change and auto-resize
   */
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    adjustTextareaHeight();
  }, [adjustTextareaHeight]);

  /**
   * Handle file input change
   */
  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        addFiles(e.target.files);
      }
      // Reset so the same file can be re-selected
      e.target.value = '';
    },
    [addFiles]
  );

  /**
   * Drag-and-drop handlers
   */
  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles]
  );

  const isSendDisabled =
    disabled || isSubmitting || isUploading || (!inputValue.trim() && pendingFiles.length === 0);

  return (
    <form
      onSubmit={handleSubmit}
      className={`border-t border-border bg-primary p-4 ${isDragOver ? 'ring-2 ring-accent ring-inset' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragOver && (
        <div className="text-center text-accent text-sm py-2 mb-2 border-2 border-dashed border-accent rounded-lg">
          Drop files here
        </div>
      )}

      {validationError && (
        <div className="mb-2 px-4 py-2 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg text-red-700 dark:text-red-300 text-sm">
          {validationError}
        </div>
      )}

      <FilePreview files={pendingFiles} onRemove={removeFile} />

      <div className="flex items-start space-x-2">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_FILE_TYPES}
          onChange={handleFileChange}
          className="hidden"
          aria-label="Attach files"
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isAtLimit}
          className="flex-shrink-0 flex items-center justify-center w-11 h-11 rounded-full text-text-secondary hover:text-text-primary hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Attach file"
          title={isAtLimit ? 'Maximum files reached' : 'Attach file'}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"
            />
          </svg>
        </button>

        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isSubmitting}
            rows={1}
            className="w-full px-4 py-2 bg-secondary text-text-primary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-border-focus focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            style={{
              minHeight: '44px',
              maxHeight: '120px',
            }}
            aria-label="Message input"
            aria-describedby="keyboard-shortcuts-help"
          />
          <div id="keyboard-shortcuts-help" className="text-xs text-text-secondary mt-1">
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>

        {isGenerating && onStopGenerating ? (
          <button
            type="button"
            onClick={handleStopGenerating}
            disabled={isStopping}
            className="flex-shrink-0 flex items-center justify-center w-11 h-11 rounded-full bg-red-600 text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-border-focus focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label={isStopping ? 'Stopping generation' : 'Stop generating'}
            title={isStopping ? 'Stopping...' : 'Stop generating'}
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" rx="1" />
            </svg>
          </button>
        ) : (
          <button
            type="submit"
            disabled={isSendDisabled}
            className="flex-shrink-0 flex items-center justify-center w-11 h-11 rounded-full bg-accent text-white hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-border-focus focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label={isSubmitting || isUploading ? (isUploading ? 'Uploading' : 'Sending') : 'Send message'}
            title={isSubmitting || isUploading ? (isUploading ? 'Uploading...' : 'Sending...') : 'Send message'}
          >
            {isSubmitting || isUploading ? (
              <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19V5m0 0l-6 6m6-6l6 6"
                />
              </svg>
            )}
          </button>
        )}
      </div>
    </form>
  );
}
