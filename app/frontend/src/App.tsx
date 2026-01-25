import { useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { logger } from './utils/logger';
import { useTheme } from './hooks/useTheme';

function App() {
  // Initialize theme system
  const { currentTheme } = useTheme();
  
  useEffect(() => {
    logger.info('Application started', {
      environment: import.meta.env.MODE,
      endpoint: import.meta.env.VITE_AGUI_ENDPOINT || '/api',
      theme: currentTheme,
    });
  }, [currentTheme]);

  return (
    <div className="min-h-screen bg-primary flex items-center justify-center p-4">
      <div className="w-full max-w-5xl h-[90vh]">
        <ChatInterface />
      </div>
    </div>
  );
}

export default App;
