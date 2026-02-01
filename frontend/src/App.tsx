import { useState, useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { ConversationSidebar, type Conversation } from './components/Sidebar';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';

function AuthenticatedApp() {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string>('default');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const { logout, user } = useAuth();

  // Initialize dark mode and conversations from localStorage
  useEffect(() => {
    const savedMode = localStorage.getItem('darkMode');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedMode === 'true' || (!savedMode && prefersDark)) {
      setIsDarkMode(true);
      document.documentElement.classList.add('dark');
    }

    // Load conversations from localStorage
    const savedConversations = localStorage.getItem('conversations');
    if (savedConversations) {
      const parsed = JSON.parse(savedConversations);
      setConversations(parsed.map((c: any) => ({
        ...c,
        // Truncate title if it's too long (for backwards compatibility)
        title: c.title && c.title.length > 30 ? c.title.slice(0, 30) + '...' : c.title,
        timestamp: new Date(c.timestamp),
      })));
    } else {
      // Add some demo conversations
      const demoConversations: Conversation[] = [
        {
          id: '1',
          title: '123',
          preview: 'Quyền lợi khi tư thái',
          timestamp: new Date(Date.now() - 3600000), // 1 hour ago
        },
        {
          id: '2',
          title: '123',
          preview: 'Thủ tục ly hôn',
          timestamp: new Date(Date.now() - 7200000), // 2 hours ago
        },
      ];
      setConversations(demoConversations);
    }
  }, []);

  // Save conversations to localStorage when they change
  useEffect(() => {
    if (conversations.length > 0) {
      try {
        localStorage.setItem('conversations', JSON.stringify(conversations));
      } catch (error) {
        console.error('Failed to save conversations to localStorage:', error);
      }
    }
  }, [conversations]);

  const handleToggleDarkMode = () => {
    setIsDarkMode((prev: boolean) => {
      const newMode = !prev;
      localStorage.setItem('darkMode', String(newMode));

      if (newMode) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }

      return newMode;
    });
  };

  const handleNewConversation = () => {
    const newId = `conv-${Date.now()}`;
    const newConversation: Conversation = {
      id: newId,
      title: 'Cuộc trò chuyện mới',
      preview: 'Bắt đầu đặt câu hỏi...',
      timestamp: new Date(),
    };

    setConversations([newConversation, ...conversations]);
    setActiveConversationId(newId);

    // Close sidebar on mobile after creating new conversation
    if (window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);

    // Close sidebar on mobile after selecting
    if (window.innerWidth < 1024) {
      setIsSidebarOpen(false);
    }
  };

  const handleDeleteConversation = (id: string) => {
    setConversations(conversations.filter((c: Conversation) => c.id !== id));

    if (activeConversationId === id) {
      // Switch to default or first conversation
      const remaining = conversations.filter((c: Conversation) => c.id !== id);
      setActiveConversationId(remaining.length > 0 ? remaining[0].id : 'default');
    }
  };

  const handleUpdateConversation = (id: string, firstMessage: string) => {
    setConversations((prev: Conversation[]) =>
      prev.map((c: Conversation) =>
        c.id === id
          ? {
            ...c,
            title: firstMessage.slice(0, 30) + (firstMessage.length > 30 ? '...' : ''),
            preview: firstMessage.slice(0, 60),
            timestamp: new Date(),
          }
          : c
      )
    );
  };

  const handlePinConversation = (id: string) => {
    setConversations((prev) =>
      prev.map((c) =>
        c.id === id ? { ...c, isPinned: !c.isPinned } : c
      )
    );
  };

  const handleRenameConversation = (id: string, newTitle: string) => {
    setConversations((prev) =>
      prev.map((c) =>
        c.id === id ? { ...c, title: newTitle.slice(0, 30) } : c
      )
    );
  };

  return (
    <div className="w-full h-screen overflow-hidden flex flex-col">
      {/* Top Bar with User Info */}


      <div className="flex-1 overflow-hidden flex">
        {/* Sidebar */}
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onNewConversation={handleNewConversation}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          onPinConversation={handlePinConversation}
          onRenameConversation={handleRenameConversation}
          isDarkMode={isDarkMode}
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        />

        {/* Main Chat Area */}
        <div className="flex-1 overflow-hidden">
          <ChatInterface
            conversationId={activeConversationId}
            isDarkMode={isDarkMode}
            onToggleDarkMode={handleToggleDarkMode}
            onUpdateConversation={handleUpdateConversation}
            user={user}
            onLogout={logout}
          />
        </div>
      </div>
    </div>
  );
}

function AppContent() {
  const { isAuthenticated } = useAuth();
  const [isRegistering, setIsRegistering] = useState(false);

  if (isAuthenticated) {
    return <AuthenticatedApp />;
  }

  if (isRegistering) {
    return <Register onRegisterSuccess={() => setIsRegistering(false)} />;
  }

  return (
    <div className="flex flex-col h-screen">
      <Login
        onLoginSuccess={() => { }}
        onRegisterClick={() => setIsRegistering(true)}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
