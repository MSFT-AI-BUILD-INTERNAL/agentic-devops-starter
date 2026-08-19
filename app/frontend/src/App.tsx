import { useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { TeamsSidebar } from './components/TeamsSidebar';
import { logger } from './utils/logger';
import { useTheme } from './hooks/useTheme';
import { getApiBaseUrl } from './config/api';

function App() {
  // Initialize theme system
  const { currentTheme } = useTheme();
  
  useEffect(() => {
    logger.info('Application started', {
      environment: import.meta.env.MODE,
      endpoint: getApiBaseUrl(),
      theme: currentTheme,
    });
  }, [currentTheme]);

  useEffect(() => {
    const apiBaseUrl = getApiBaseUrl();
    void fetch(`${apiBaseUrl}/auth/session`, { credentials: 'include' }).then((response) => {
      if (response.status === 401) {
        window.location.assign(`${apiBaseUrl}/auth/login`);
      }
    });
  }, []);

  return (
    <div className="min-h-screen bg-primary flex">
      <TeamsSidebar />
      <div className="flex-1 flex flex-col h-screen">
        <ChatInterface />
      </div>
    </div>
  );
}

export default App;
