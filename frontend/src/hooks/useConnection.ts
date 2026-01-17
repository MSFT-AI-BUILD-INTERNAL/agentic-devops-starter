// useConnection hook for backend status tracking
import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '../stores/chatStore';
import { streamHandler } from '../services/streamHandler';
import { aguiClient } from '../services/aguiClient';
import { logger } from '../utils/logger';

const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY = 1000; // 1 second
const MAX_RECONNECT_DELAY = 30000; // 30 seconds

export function useConnection() {
  const connection = useChatStore((state) => state.connection);
  const setConnectionStatus = useChatStore((state) => state.setConnectionStatus);
  const currentThread = useChatStore((state) => state.currentThread);

  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  /**
   * Connect to backend SSE stream
   */
  const connect = useCallback(() => {
    logger.info('Attempting to connect to backend', {
      threadId: currentThread?.id || 'new',
      attempt: reconnectAttemptsRef.current + 1,
    });

    setConnectionStatus('connecting');

    streamHandler.connect(
      currentThread?.id || null,
      // onOpen
      () => {
        logger.info('Connection established');
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
      },
      // onError
      () => {
        logger.error('Connection error occurred');
        setConnectionStatus('disconnected');

        // Schedule reconnect inline to avoid dependency issue
        if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
          logger.error('Max reconnection attempts reached', undefined, {
            attempts: reconnectAttemptsRef.current,
          });
          setConnectionStatus(
            'error',
            'Unable to connect to backend. Please check your connection.'
          );
          return;
        }

        const delay = Math.min(
          INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current),
          MAX_RECONNECT_DELAY
        );
        reconnectAttemptsRef.current++;

        logger.info('Scheduling reconnection', {
          attempt: reconnectAttemptsRef.current,
          delayMs: delay,
        });

        setConnectionStatus('reconnecting', `Reconnecting in ${delay / 1000}s...`);

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    );
  }, [currentThread?.id, setConnectionStatus]);

  /**
   * Disconnect from backend
   */
  const disconnect = useCallback(() => {
    logger.info('Disconnecting from backend');

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    streamHandler.disconnect();
    setConnectionStatus('disconnected');
    reconnectAttemptsRef.current = 0;
  }, [setConnectionStatus]);

  /**
   * Manual reconnect (resets attempt counter)
   */
  const reconnect = useCallback(() => {
    logger.info('Manual reconnect triggered');
    reconnectAttemptsRef.current = 0;
    disconnect();
    setTimeout(connect, 500);
  }, [connect, disconnect]);

  /**
   * Check backend health
   */
  const checkHealth = useCallback(async () => {
    try {
      const health = await aguiClient.checkHealth();
      logger.info('Backend health check passed', { health });
      return true;
    } catch (error) {
      logger.error('Backend health check failed', error);
      return false;
    }
  }, []);

  /**
   * Monitor online/offline status
   */
  useEffect(() => {
    const handleOnline = () => {
      logger.info('Network is online');
      reconnect();
    };

    const handleOffline = () => {
      logger.warn('Network is offline');
      setConnectionStatus('disconnected', 'No internet connection');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [reconnect, setConnectionStatus]);

  /**
   * Initial connection on mount
   */
  useEffect(() => {
    const connectOnMount = () => {
      connect();
    };

    connectOnMount();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    status: connection.status,
    errorMessage: connection.errorMessage,
    reconnectAttempts: connection.reconnectAttempts,
    connect,
    disconnect,
    reconnect,
    checkHealth,
    isConnected: connection.status === 'connected',
  };
}
