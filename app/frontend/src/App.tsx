import { useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { logger } from './utils/logger';

function App() {
  useEffect(() => {
    logger.info('Application started', {
      environment: import.meta.env.MODE,
      endpoint: import.meta.env.VITE_AGUI_ENDPOINT || '/api',
    });
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="w-full max-w-5xl h-[90vh]">
        <ChatInterface />
      </div>
    </div>
  );
}

export default App;
