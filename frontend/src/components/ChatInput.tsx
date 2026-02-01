import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'motion/react';
import { Send, Zap, Crown, ChevronDown } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isDarkMode: boolean;
  mode?: 'summary' | 'detail';
  onModeChange?: (mode: 'summary' | 'detail') => void;
}

export function ChatInput({ onSend, disabled, isDarkMode, mode = 'summary', onModeChange }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isDropdownOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.top,
        left: rect.left,
        width: 240
      });
    }
  }, [isDropdownOpen]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  // Removed conflicting click-outside listener as we use a fixed overlay now

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const modes = [
    { id: 'summary' as const, label: 'Summary', icon: Zap, color: 'from-blue-500 to-cyan-500' },
    { id: 'detail' as const, label: 'Detail', icon: Crown, color: 'from-purple-500 to-pink-500' },
  ];

  const currentMode = modes.find(m => m.id === mode) || modes[0];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="relative z-50"
    >
      {/* Glassmorphic Container - ChatGPT Style */}
      <div
        className={`relative overflow-visible rounded-3xl backdrop-blur-xl border transition-all duration-300 ${isFocused
          ? 'bg-white/90 dark:bg-gray-800/90 border-gray-300/60 dark:border-gray-600/60 shadow-lg'
          : 'bg-white/70 dark:bg-gray-800/70 border-gray-300/50 dark:border-gray-700/50 shadow-md'
          }`}
      >
        {/* Animated Gradient Background */}
        <motion.div
          animate={{
            background: isFocused
              ? [
                'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1))',
                'linear-gradient(225deg, rgba(6,182,212,0.1), rgba(59,130,246,0.1))',
                'linear-gradient(315deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1))',
              ]
              : 'linear-gradient(135deg, rgba(0,0,0,0), rgba(0,0,0,0))',
          }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          className="absolute inset-0 pointer-events-none rounded-3xl"
        />

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="relative z-10">
          <div className="flex items-center gap-2 px-4 py-3">
            {/* Mode Selector Dropdown - Inside Input, Clean Style */}
            {onModeChange && (
              <div className="relative flex-shrink-0" ref={dropdownRef}>
                <motion.button
                  ref={buttonRef}
                  type="button"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className={`relative z-20 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-all duration-200 ${isDropdownOpen
                    ? 'bg-gray-200 dark:bg-gray-700'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700/50'
                    }`}
                >
                  <currentMode.icon size={14} className="text-gray-600 dark:text-gray-400" />
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{currentMode.label}</span>
                  <ChevronDown
                    size={12}
                    className={`text-gray-500 dark:text-gray-400 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''
                      }`}
                  />
                </motion.button>

                {/* Dropdown Menu - Portal to render outside */}
                {isDropdownOpen && (
                  <div className="fixed inset-0 z-[9998]" onClick={() => setIsDropdownOpen(false)} />
                )}
                {isDropdownOpen && buttonRef.current && createPortal(
                  (() => {
                    const buttonRect = buttonRef.current!.getBoundingClientRect();

                    return (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.15, ease: 'easeOut' }}
                        style={{
                          position: 'fixed',
                          bottom: `${window.innerHeight - buttonRect.top + 8}px`,
                          right: `${window.innerWidth - buttonRect.right}px`,
                          width: '240px',
                          zIndex: 9999
                        }}
                        className={`rounded-2xl backdrop-blur-xl border shadow-2xl overflow-visible ${isDarkMode
                          ? 'bg-gray-800/95 border-gray-700/60'
                          : 'bg-white/95 border-gray-200/80'
                          }`}
                      >
                        {modes.map((m) => {
                          const ModeIcon = m.icon;
                          return (
                            <motion.button
                              key={m.id}
                              type="button"
                              whileHover={{ backgroundColor: isDarkMode ? 'rgba(55, 65, 81, 0.6)' : 'rgba(243, 244, 246, 0.8)' }}
                              onClick={() => {
                                onModeChange(m.id);
                                setIsDropdownOpen(false);
                              }}
                              className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-all duration-150 border-b last:border-b-0 ${isDarkMode ? 'border-gray-700/50' : 'border-gray-200/50'
                                } ${mode === m.id
                                  ? isDarkMode
                                    ? 'bg-blue-500/10'
                                    : 'bg-blue-50/80'
                                  : ''
                                }`}
                            >
                              <div className={`mt-0.5 p-1.5 rounded-lg ${m.id === 'summary' ? 'bg-blue-500/20' : 'bg-purple-500/20'}`}>
                                <ModeIcon size={16} className={m.id === 'summary' ? 'text-blue-600 dark:text-blue-400' : 'text-purple-600 dark:text-purple-400'} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                                    {m.id === 'summary' ? 'Summary' : 'Detail'}
                                  </span>
                                  {mode === m.id && (
                                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                                  )}
                                </div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                                  {m.id === 'summary' ? 'Tóm tắt nhanh' : 'Phân tích chi tiết'}
                                </p>
                              </div>
                            </motion.button>
                          );
                        })}
                      </motion.div>
                    );
                  })(),
                  document.body
                )}
              </div>
            )}

            {/* Textarea */}
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                disabled={disabled}
                placeholder="Nhập câu hỏi của bạn..."
                rows={1}
                className="w-full bg-transparent resize-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 max-h-[200px] disabled:opacity-50"
                style={{ minHeight: '24px' }}
              />
            </div>

            {/* Send Button - ChatGPT Style */}
            <motion.button
              type="submit"
              disabled={disabled || !message.trim()}
              whileHover={{ scale: message.trim() && !disabled ? 1.05 : 1 }}
              whileTap={{ scale: message.trim() && !disabled ? 0.95 : 1 }}
              className={`relative overflow-hidden rounded-xl p-2 transition-all duration-300 ${message.trim() && !disabled
                ? 'bg-blue-500 hover:bg-blue-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                }`}
            >
              <Send size={18} className="relative z-10" />
            </motion.button>
          </div>
        </form>
      </div>


    </motion.div>
  );
}