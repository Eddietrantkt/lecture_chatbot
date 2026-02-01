import { motion } from 'motion/react';
import { User, Sparkles } from 'lucide-react';
import { MessageContent } from './MessageContent';

interface ChatMessageProps {
  message: {
    id: string;
    text: string;
    sender: 'user' | 'ai';
    timestamp: Date;
    pdf_sources?: Array<{ json_file?: string; pdf_file?: string; article_num?: string; page_num?: number }>;
    candidates?: string[];
  };
  isDarkMode: boolean;
  onOpenPDF?: (url: string, title: string, articleNum?: string, pageNum?: number) => void;
  onSelectQuestion?: (question: string) => void;
}

export function ChatMessage({ message, isDarkMode, onOpenPDF, onSelectQuestion }: ChatMessageProps) {
  const isUser = message.sender === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
      className={`flex items-start gap-4 ${isUser ? 'flex-row-reverse' : ''} max-w-full`}
    >
      {/* Avatar with Glass Effect */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1, type: 'spring', stiffness: 200, damping: 15 }}
        className={`relative w-10 h-10 rounded-2xl flex items-center justify-center flex-shrink-0 overflow-hidden ${isUser
          ? 'bg-gradient-to-br from-purple-500 via-pink-500 to-orange-500'
          : 'bg-gradient-to-br from-blue-500 via-cyan-500 to-teal-500'
          } shadow-lg`}
      >
        <div className="absolute inset-0 bg-white/20 backdrop-blur-sm" />
        {isUser ? (
          <User size={20} className="text-white relative z-10" />
        ) : (
          <Sparkles size={20} className="text-white relative z-10" />
        )}
      </motion.div>

      {/* Message Bubble with Glass Effect */}
      <motion.div
        initial={{ opacity: 0, x: isUser ? 20 : -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.15, duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
        className={`relative max-w-[85%] md:max-w-[75%] group ${isUser ? 'items-end' : 'items-start'}`}
      >
        {/* Glassmorphic Container */}
        <div
          className={`relative overflow-hidden rounded-3xl p-4 backdrop-blur-xl border ${isUser
            ? 'bg-gradient-to-br from-purple-500/90 via-pink-500/90 to-orange-500/90 border-white/30 text-white shadow-xl shadow-purple-500/25'
            : 'bg-white/70 dark:bg-gray-800/70 border-gray-200/50 dark:border-gray-700/50 text-gray-900 dark:text-gray-100 shadow-xl shadow-gray-500/10 dark:shadow-gray-900/30'
            }`}
        >
          {/* Animated Gradient Overlay */}
          <div
            className={`absolute inset-0 opacity-30 ${isUser
              ? 'bg-gradient-to-br from-white/40 via-transparent to-transparent'
              : 'bg-gradient-to-br from-blue-500/20 via-cyan-500/20 to-transparent dark:from-blue-400/10 dark:via-cyan-400/10'
              }`}
          />

          {/* Liquid Effect Border */}
          <motion.div
            animate={{
              background: isUser
                ? [
                  'linear-gradient(45deg, rgba(255,255,255,0.3), rgba(255,255,255,0.1))',
                  'linear-gradient(90deg, rgba(255,255,255,0.1), rgba(255,255,255,0.3))',
                  'linear-gradient(135deg, rgba(255,255,255,0.3), rgba(255,255,255,0.1))',
                ]
                : [
                  'linear-gradient(45deg, rgba(59,130,246,0.2), rgba(6,182,212,0.2))',
                  'linear-gradient(90deg, rgba(6,182,212,0.2), rgba(59,130,246,0.2))',
                  'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(6,182,212,0.2))',
                ],
            }}
            transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
            className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
          />

          {/* Message Content */}
          <div className={`relative z-10 break-words overflow-hidden ${isUser ? 'whitespace-pre-wrap' : ''}`}>
            {isUser ? (
              // User message: render as plain text (keep whitespace-pre-wrap)
              message.text
            ) : (
              // AI message: render with Markdown (ReactMarkdown handles spacing)
              <MessageContent
                text={message.text}
                pdfSources={message.pdf_sources}
                onOpenPDF={onOpenPDF}
              />
            )}

            {/* Candidate Suggestions */}
            {!isUser && message.candidates && message.candidates.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2 relative z-20">
                {message.candidates.map((candidate, index) => (
                  <button
                    key={index}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectQuestion?.(candidate);
                    }}
                    className="px-3 py-1.5 rounded-full text-xs font-medium bg-blue-500/10 hover:bg-blue-500/20 text-blue-700 dark:text-blue-300 border border-blue-500/30 transition-colors cursor-pointer"
                  >
                    {candidate}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Time Stamp */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            transition={{ delay: 0.5 }}
            className={`text-xs mt-2 ${isUser ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'}`}
          >
            {message.timestamp.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
          </motion.div>
        </div>
      </motion.div>
    </motion.div>
  );
}
