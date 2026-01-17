// Logger utility with correlation ID support

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  correlationId?: string;
  component?: string;
  [key: string]: unknown;
}

class Logger {
  private correlationId: string | null = null;
  private component: string = 'Frontend';

  /**
   * Set correlation ID for all subsequent logs
   */
  setCorrelationId(id: string): void {
    this.correlationId = id;
  }

  /**
   * Clear correlation ID
   */
  clearCorrelationId(): void {
    this.correlationId = null;
  }

  /**
   * Set component name for all logs
   */
  setComponent(name: string): void {
    this.component = name;
  }

  /**
   * Generate a new correlation ID
   */
  generateCorrelationId(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }

  /**
   * Format log message with context
   */
  private formatMessage(level: LogLevel, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const correlationId = context?.correlationId || this.correlationId || 'N/A';
    const component = context?.component || this.component;

    let formatted = `[${timestamp}] [${level.toUpperCase()}] [${component}] [${correlationId}] ${message}`;

    // Add additional context if provided
    if (context) {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { correlationId: _unused1, component: _unused2, ...rest } = context;
      if (Object.keys(rest).length > 0) {
        formatted += ` ${JSON.stringify(rest)}`;
      }
    }

    return formatted;
  }

  /**
   * Log debug message
   */
  debug(message: string, context?: LogContext): void {
    if (import.meta.env.DEV || import.meta.env.VITE_DEBUG_MODE) {
      console.debug(this.formatMessage('debug', message, context));
    }
  }

  /**
   * Log info message
   */
  info(message: string, context?: LogContext): void {
    console.info(this.formatMessage('info', message, context));
  }

  /**
   * Log warning message
   */
  warn(message: string, context?: LogContext): void {
    console.warn(this.formatMessage('warn', message, context));
  }

  /**
   * Log error message
   */
  error(message: string, error?: Error | unknown, context?: LogContext): void {
    const errorContext = {
      ...context,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    };
    console.error(this.formatMessage('error', message, errorContext));
  }
}

// Export singleton instance
export const logger = new Logger();

// Export types for use in other modules
export type { LogLevel, LogContext };
