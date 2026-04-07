import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { DarkModeToggle } from './DarkModeToggle';
import { PDFViewer } from './PDFViewer';
import { ScrollArea } from './ui/scroll-area';
import { Button } from './ui/button';
import { ThumbsUp, ThumbsDown, Zap, Clock, Scale, LogOut } from 'lucide-react';
import { WelcomeScreen } from './WelcomeScreen';
import { LoadingDots } from './LoadingDots';
import { askQuestion, clarifySubject, submitFeedback as apiSubmitFeedback, suggestQuestions, type AnswerResponse } from '../services/api';
import { SuggestedQuestions } from './SuggestedQuestions';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  sources?: Array<{
    title: string;
    page?: string;
    pdfUrl?: string;
    articleNum?: string;
  }>;
  pdf_sources?: any[];
  context?: Array<{ source: string; content: string }>;
  feedback?: 'up' | 'down' | null;
  timing_ms?: number;
  search_method?: string;
  candidates?: Array<{ code: string; name: string }>;
  clarification_question?: string;
}

interface User {
  username: string;
  email?: string;
  full_name?: string;
}

interface ChatInterfaceProps {
  conversationId: string;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onOpenPDF?: (pdfUrl: string, title: string, articleNum?: string, pageNum?: number) => void;
  onUpdateConversation?: (id: string, firstMessage: string) => void;
  user?: User | null;
  onLogout?: () => void;
}

const formatLawName = (jsonFile: string | undefined): string => {
  if (!jsonFile) return 'Văn bản pháp luật';

  const nameMap: Record<string, string> = {
    'luat_lao_donghopnhat.json': 'Bộ luật Lao động',
    'luat_so_huu_tri_tue_hopnhat.json': 'Bộ luật Sở hữu trí tuệ',
    'luat_dat_dai_hopnhat.json': 'Luật Đất đai',
    'luat_dat_dai.json': 'Luật Đất đai',
    'luat_hon_nhan_hopnhat.json': 'Luật Hôn nhân và Gia đình',
    'luat_hon_nhan.json': 'Luật Hôn nhân và Gia đình',
    'luat_dauthau_hopnhat.json': 'Luật Đấu thầu',
    'luat_dau_thau.json': 'Luật Đấu thầu',
    'chuyen_giao_cong_nghe_hopnhat.json': 'Luật Chuyển giao công nghệ',
    'chuyen_giao_cong_nghe.json': 'Luật Chuyển giao công nghệ',
    'nghi_dinh_214_2025.json': 'Nghị định 214/2025/NĐ-CP',
    'luat_hinh_su_hopnhat.json': 'Bộ luật Hình sự',
  };

  return nameMap[jsonFile] || jsonFile.replace(/_hopnhat\.json|\.json/g, '').replace(/_/g, ' ');
};

export function ChatInterface({
  conversationId,
  isDarkMode,
  onToggleDarkMode,
  onOpenPDF,
  onUpdateConversation,
  user,
  onLogout
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [mode, setMode] = useState<'summary' | 'detail'>('summary');
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [pdfViewer, setPdfViewer] = useState<{
    isOpen: boolean;
    url: string;
    title: string;
    articleNum?: string;
    pageNum?: number;
  }>({
    isOpen: false,
    url: '',
    title: '',
    articleNum: undefined,
    pageNum: undefined,
  });
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);

  // Load messages from localStorage when conversationId changes
  useEffect(() => {
    const savedMessages = localStorage.getItem(`messages_${conversationId}`);
    if (savedMessages) {
      try {
        const parsed = JSON.parse(savedMessages);
        setMessages(parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        })));
      } catch (error) {
        console.error('Failed to parse saved messages:', error);
        // Fallback to default message
        setMessages([
          {
            id: '1',
            text: 'Xin chào! Tôi là trợ lý môn học AI. Tôi có thể giúp bạn tư vấn về các vấn đề môn học khoa toán-tin trường đại học Khoa học tự nhiên. Bạn có câu hỏi gì không?',
            sender: 'ai',
            timestamp: new Date(),
          },
        ]);
      }
    } else {
      // New conversation - set default message
      setMessages([
        {
          id: '1',
          text: 'Xin chào! Tôi là trợ lý môn học AI. Tôi có thể giúp bạn tư vấn về các vấn đề môn học khoa toán-tin trường đại học Khoa học tự nhiên. Bạn có câu hỏi gì không?',
          sender: 'ai',
          timestamp: new Date(),
        },
      ]);
    }
    setChatHistory([]);
    setSuggestedQuestions([]);
  }, [conversationId]);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      try {
        localStorage.setItem(`messages_${conversationId}`, JSON.stringify(messages));
      } catch (error) {
        if (error instanceof DOMException &&
          (error.name === 'QuotaExceededError' || error.name === 'NS_ERROR_DOM_QUOTA_REACHED')) {
          console.warn('Storage quota exceeded. Attempting to clear old messages...');
          try {
            // Try enabling a "safe mode" - only save the last 20 messages
            const recentMessages = messages.slice(-20);
            localStorage.setItem(`messages_${conversationId}`, JSON.stringify(recentMessages));
          } catch (retryError) {
            console.error('Failed to save messages even after trimming:', retryError);
          }
        } else {
          console.error('Error saving messages:', error);
        }
      }
    }
  }, [messages, conversationId]);

  // Improved scroll logic - scroll to bottom when new messages arrive
  useEffect(() => {
    // Use requestAnimationFrame to ensure DOM is updated
    const timeoutId = setTimeout(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'end'
        });
      }
    }, 0);

    return () => clearTimeout(timeoutId);
  }, [messages, isTyping]);

  // Track if user is scrolling manually - only auto scroll if near bottom
  useEffect(() => {
    const scrollElement = document.querySelector('[data-slot="scroll-area-viewport"]') as HTMLElement;

    if (!scrollElement) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = scrollElement;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 150;
      shouldAutoScrollRef.current = isNearBottom;
    };

    scrollElement.addEventListener('scroll', handleScroll);
    return () => scrollElement.removeEventListener('scroll', handleScroll);
  }, []);

  const handleOpenPDF = (pdfUrl: string, title: string, articleNum?: string, pageNum?: number) => {
    if (onOpenPDF) {
      onOpenPDF(pdfUrl, title, articleNum, pageNum);
    } else {
      setPdfViewer({ isOpen: true, url: pdfUrl, title, articleNum, pageNum });
    }
  };

  const buildDisplaySources = (response: AnswerResponse) => (
    (response.pdf_sources || []).slice(0, 3).map((pdfSource) => ({
      title: formatLawName(pdfSource.json_file),
      page: pdfSource.article_num ? `Điều ${pdfSource.article_num}` : undefined,
      pdfUrl: pdfSource.pdf_file,
      articleNum: pdfSource.article_num?.toString(),
    }))
  );

  const handleSendMessage = async (text: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);
    setSuggestedQuestions([]); // Clear old suggestions

    // Update conversation title with first message
    if (onUpdateConversation && messages.length <= 1) {
      onUpdateConversation(conversationId, text);
    }

    try {
      // ✅ Build context from last 2 Q&A pairs (4 messages)
      const recentMessages = messages.slice(-4);
      let previousContext = '';
      if (recentMessages.length > 0) {
        previousContext = recentMessages
          .map((msg) => `${msg.sender === 'user' ? 'Q' : 'A'}: ${msg.text.slice(0, 200)}`)
          .join(' | ');
      }

      const response = await askQuestion(text, conversationId, mode, chatHistory, previousContext);

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.answer,
        sender: 'ai',
        timestamp: new Date(),
        sources: buildDisplaySources(response),
        pdf_sources: response.pdf_sources || [],
        context: response.sources,
        feedback: null,
        timing_ms: response.timing_ms,
        search_method: response.search_method,
        candidates: response.candidates,
        clarification_question: response.need_clarification ? text : undefined,
      };

      setMessages((prev) => [...prev, aiMessage]);

      setChatHistory([
        ...chatHistory,
        { role: 'user', content: text },
        { role: 'assistant', content: response.answer },
      ]);

      // ✅ Get suggested questions after answer
      try {
        const suggestions = await suggestQuestions(text, response.answer, 3);
        setSuggestedQuestions(suggestions);
      } catch (err) {
        console.error('Error getting suggestions:', err);
      }
    } catch (error) {
      console.error('Error asking question:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Xin lỗi, đã có lỗi xảy ra khi xử lý câu hỏi của bạn. Vui lòng thử lại.',
        sender: 'ai',
        timestamp: new Date(),
        feedback: null,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSelectCandidate = async (
    candidate: { code: string; name: string },
    originalQuestion: string
  ) => {
    if (isTyping) return;

    const selectionText = `Tôi chọn ${candidate.name} (${candidate.code})`;
    const userMessage: Message = {
      id: Date.now().toString(),
      text: selectionText,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);
    setSuggestedQuestions([]);

    try {
      const response = await clarifySubject(conversationId, candidate.code, originalQuestion);

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.answer,
        sender: 'ai',
        timestamp: new Date(),
        sources: buildDisplaySources(response),
        pdf_sources: response.pdf_sources || [],
        context: response.sources,
        feedback: null,
        timing_ms: response.timing_ms,
        search_method: response.search_method,
      };

      setMessages((prev) => [...prev, aiMessage]);
      setChatHistory([
        ...chatHistory,
        { role: 'user', content: originalQuestion },
        { role: 'assistant', content: response.answer },
      ]);

      try {
        const suggestions = await suggestQuestions(originalQuestion, response.answer, 3);
        setSuggestedQuestions(suggestions);
      } catch (err) {
        console.error('Error getting suggestions:', err);
      }
    } catch (error) {
      console.error('Error clarifying subject:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Xin lỗi, đã có lỗi xảy ra khi xử lý lựa chọn của bạn. Vui lòng thử lại.',
        sender: 'ai',
        timestamp: new Date(),
        feedback: null,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleFeedback = async (messageId: string, feedback: 'up' | 'down') => {
    const message = messages.find((msg) => msg.id === messageId);
    if (!message || !message.context) return;

    const newFeedback = message.feedback === feedback ? null : feedback;

    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, feedback: newFeedback } : msg))
    );

    if (newFeedback) {
      try {
        const messageIndex = messages.findIndex((msg) => msg.id === messageId);
        let userQuestion = '';

        for (let i = messageIndex - 1; i >= 0; i--) {
          if (messages[i].sender === 'user') {
            userQuestion = messages[i].text;
            break;
          }
        }

        await apiSubmitFeedback(
          userQuestion,
          message.text,
          message.context,
          newFeedback === 'up' ? 'like' : 'dislike'
        );

        console.log('Feedback submitted successfully');
      } catch (error) {
        console.error('Error submitting feedback:', error);
      }
    }
  };

  return (
    <div className="h-full flex flex-col relative overflow-hidden">
      {/* Animated Background with Glass Effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-cyan-50 to-teal-50 dark:from-gray-950 dark:via-blue-950 dark:to-purple-950">
        {/* Floating Orbs */}
        <motion.div
          animate={{
            x: [0, 100, 0],
            y: [0, -100, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="absolute top-20 left-20 w-96 h-96 bg-gradient-to-br from-blue-400/30 to-cyan-400/30 dark:from-blue-500/20 dark:to-cyan-500/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            x: [0, -100, 0],
            y: [0, 100, 0],
            scale: [1, 1.3, 1],
          }}
          transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
          className="absolute bottom-20 right-20 w-[32rem] h-[32rem] bg-gradient-to-br from-purple-400/30 to-pink-400/30 dark:from-purple-500/20 dark:to-pink-500/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            x: [0, 50, 0],
            y: [0, -50, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
          className="absolute top-1/2 left-1/2 w-80 h-80 bg-gradient-to-br from-teal-400/30 to-green-400/30 dark:from-teal-500/20 dark:to-green-500/20 rounded-full blur-3xl"
        />
      </div>

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col">
        {/* Header with Glass Effect - FIXED POSITION, NO ANIMATION ON CONVERSATION CHANGE */}
        <div className="flex-shrink-0 backdrop-blur-2xl bg-white/60 dark:bg-gray-900/60 border-b border-white/50 dark:border-gray-700/50 px-6 py-5">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Logo with Glass Effect */}
              <motion.div
                whileHover={{ scale: 1.05, rotate: 5 }}
                className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 via-cyan-500 to-teal-500 flex items-center justify-center shadow-xl shadow-blue-500/30 relative overflow-hidden"
              >
                <div className="absolute inset-0 bg-white/20 backdrop-blur-sm" />
                <Scale size={24} className="text-white relative z-10" />
              </motion.div>

              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  AI Đề cương Học phần
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Hỗ trợ tra cứu thông tin môn học
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <DarkModeToggle isDark={isDarkMode} onToggle={onToggleDarkMode} />

              {user && onLogout && (
                <div className="flex items-center gap-3 border-l border-gray-200 dark:border-gray-700 pl-3 ml-1">
                  <div className="hidden md:flex flex-col items-end mr-1">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{user.username}</span>
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onLogout}
                    title="Đăng xuất"
                    className="p-2 rounded-xl bg-red-50 text-red-500 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30 transition-colors"
                  >
                    <LogOut size={18} />
                  </motion.button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Messages Area - ANIMATE ONLY THIS PART */}
        <div className="flex-1 relative" key={conversationId}>
          <div className="absolute inset-0">
            <ScrollArea className="h-full">
              <div className="max-w-4xl w-full mx-auto p-6 space-y-6">
                {/* Welcome Screen - Hiển thị khi chỉ có tin nhắn chào mừng */}
                <AnimatePresence>
                  {messages.length === 1 && messages[0].sender === 'ai' && (
                    <WelcomeScreen
                      isDarkMode={isDarkMode}
                      onSelectQuestion={handleSendMessage}
                    />
                  )}
                </AnimatePresence>

                <AnimatePresence mode="popLayout">
                  {messages.map((message) => (
                    <motion.div
                      key={message.id}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <ChatMessage
                        message={message}
                        isDarkMode={isDarkMode}
                        onOpenPDF={handleOpenPDF}
                        onSelectCandidate={handleSelectCandidate}
                      />

                      {/* Feedback Buttons - Show for AI messages */}
                      {message.sender === 'ai' && (
                        <>
                          {/* Feedback Buttons with Glass Effect */}
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: message.feedback ? 0 : 1 }}
                            className={`flex items-center gap-2 mt-4 ml-14 transition-all duration-500 ${message.feedback ? 'pointer-events-none' : ''
                              }`}
                          >
                            <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleFeedback(message.id, 'up')}
                                className="gap-2 backdrop-blur-xl bg-white/60 dark:bg-gray-800/60 hover:bg-green-500/20 border border-white/50 dark:border-gray-700/50 rounded-2xl"
                              >
                                <ThumbsUp size={16} />
                                <span>Hữu ích</span>
                              </Button>
                            </motion.div>
                            <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleFeedback(message.id, 'down')}
                                className="gap-2 backdrop-blur-xl bg-white/60 dark:bg-gray-800/60 hover:bg-red-500/20 border border-white/50 dark:border-gray-700/50 rounded-2xl"
                              >
                                <ThumbsDown size={16} />
                                <span>Chưa tốt</span>
                              </Button>
                            </motion.div>
                          </motion.div>

                          {/* Feedback Response */}
                          <AnimatePresence>
                            {message.feedback && (
                              <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mt-4 ml-14"
                              >
                                <div
                                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-2xl backdrop-blur-xl border ${message.feedback === 'up'
                                    ? 'bg-green-500/20 border-green-500/50 text-green-700 dark:text-green-400'
                                    : 'bg-red-500/20 border-red-500/50 text-red-700 dark:text-red-400'
                                    }`}
                                >
                                  {message.feedback === 'up' ? (
                                    <>
                                      <ThumbsUp size={14} />
                                      <span>Cảm ơn phản hồi của bạn!</span>
                                    </>
                                  ) : (
                                    <>
                                      <ThumbsDown size={14} />
                                      <span>Chúng tôi sẽ cải thiện!</span>
                                    </>
                                  )}
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>

                          {/* Timing Info */}
                          {message.timing_ms && (
                            <motion.div
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              transition={{ delay: 0.4 }}
                              className="mt-3 flex justify-end"
                            >
                              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-2xl backdrop-blur-xl bg-white/60 dark:bg-gray-800/60 border border-white/50 dark:border-gray-700/50 text-xs text-gray-600 dark:text-gray-400">
                                <Clock size={12} />
                                <span>{(message.timing_ms / 1000).toFixed(2)}s</span>
                                {message.timing_ms < 2000 && (
                                  <Zap size={12} className="text-green-500" />
                                )}
                              </div>
                            </motion.div>
                          )}
                        </>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>

                {/* Typing Indicator with Glass Effect */}
                <AnimatePresence>
                  {isTyping && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="flex items-start gap-4"
                    >
                      <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-500 via-cyan-500 to-teal-500 flex items-center justify-center shadow-lg relative overflow-hidden">
                        <div className="absolute inset-0 bg-white/20 backdrop-blur-sm" />
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                          className="relative z-10"
                        >
                          <Zap size={20} className="text-white" />
                        </motion.div>
                      </div>

                      <div className="relative overflow-hidden rounded-3xl p-4 backdrop-blur-xl bg-white/70 dark:bg-gray-800/70 border border-gray-200/50 dark:border-gray-700/50 shadow-xl">
                        <LoadingDots />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* Input Area - FIXED POSITION, NO ANIMATION ON CONVERSATION CHANGE */}
        <div className="flex-shrink-0 py-4 px-4">
          <div className="max-w-4xl mx-auto">
            {/* Suggested Questions - Hiển thị sau mỗi câu trả lời */}
            {suggestedQuestions.length > 0 && (
              <SuggestedQuestions
                questions={suggestedQuestions}
                onSelectQuestion={handleSendMessage}
                onClear={() => setSuggestedQuestions([])}
                isDarkMode={isDarkMode}
              />
            )}

            <ChatInput onSend={handleSendMessage} disabled={isTyping} isDarkMode={isDarkMode} mode={mode} onModeChange={setMode} />
          </div>
        </div>
      </div>

      {/* PDF Viewer */}
      <PDFViewer
        isOpen={pdfViewer.isOpen}
        url={pdfViewer.url}
        title={pdfViewer.title}
        articleNum={pdfViewer.articleNum}
        pageNum={pdfViewer.pageNum}
        onClose={() => setPdfViewer({ isOpen: false, url: '', title: '', articleNum: undefined, pageNum: undefined })}
      />
    </div>
  );
}
