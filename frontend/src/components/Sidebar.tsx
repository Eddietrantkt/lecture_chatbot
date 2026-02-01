import { motion, AnimatePresence } from 'motion/react';
import { Plus, MessageSquare, ChevronLeft, Menu, MoreVertical, Pin, Edit3, Trash2 } from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { useState } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

export interface Conversation {
  id: string;
  title: string;
  preview: string;
  timestamp: Date;
  isPinned?: boolean;
}

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeConversationId: string;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onPinConversation?: (id: string) => void;
  onRenameConversation?: (id: string, newTitle: string) => void;
  isDarkMode: boolean;
  isOpen: boolean;
  onToggle: () => void;
}

interface SidebarItemProps {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onRename?: (id: string, newTitle: string) => void;
  onPin?: (id: string) => void;
  onDelete: (id: string) => void;
  isRenaming: boolean;
  onRenameStart: () => void;
  onRenameCancel: () => void;
  renameValue: string;
  setRenameValue: (value: string) => void;
  index: number;
}

function SidebarItem({
  conversation,
  isActive,
  onSelect,
  onRename,
  onPin,
  onDelete,
  isRenaming,
  onRenameStart,
  onRenameCancel,
  renameValue,
  setRenameValue,
  index,
}: SidebarItemProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ delay: index * 0.05 }}
      className="mb-2 last:mb-0 px-2 w-full max-w-full"
    >
      <div
        className={`group relative overflow-hidden rounded-xl border transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${isActive
          ? 'bg-blue-100/90 dark:bg-blue-900/50 text-blue-900 dark:text-blue-100 border-blue-200 dark:border-blue-700/50 shadow-sm'
          : 'bg-gray-50/50 dark:bg-gray-800/40 hover:bg-white dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200/60 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm'
          }`}
      >
        <div className="flex items-center gap-3 px-3 py-3 cursor-pointer w-full" onClick={onSelect}>
          {/* Icon */}
          <div className="flex-shrink-0">
            <MessageSquare size={18} className={isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 group-hover:text-gray-600 dark:text-gray-500 dark:group-hover:text-gray-400'} />
          </div>

          {/* Title */}
          {isRenaming ? (
            <input
              type="text"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onBlur={() => {
                if (onRename && renameValue.trim()) {
                  onRename(conversation.id, renameValue.trim());
                }
                onRenameCancel();
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  if (onRename && renameValue.trim()) {
                    onRename(conversation.id, renameValue.trim());
                  }
                  onRenameCancel();
                } else if (e.key === 'Escape') {
                  onRenameCancel();
                }
              }}
              autoFocus
              onClick={(e) => e.stopPropagation()}
              className="flex-1 min-w-0 text-sm bg-transparent border-b border-blue-500 focus:outline-none"
            />
          ) : (
            <div className="flex-1 min-w-0">
              <h4
                className={`text-sm font-medium ${isActive ? 'text-blue-900 dark:text-blue-100' : ''}`}
                title={conversation.title}
              >
                {conversation.title.length > 20
                  ? conversation.title.slice(0, 20) + '...'
                  : conversation.title}
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5 opacity-80">
                {(conversation.preview || 'Không có bản xem trước').length > 25
                  ? (conversation.preview || 'Không có bản xem trước').slice(0, 25) + '...'
                  : (conversation.preview || 'Không có bản xem trước')}
              </p>
            </div>
          )}

          {/* Pin indicator */}
          {conversation.isPinned && (
            <Pin size={14} className={`flex-shrink-0 ${isActive ? 'text-blue-500 dark:text-blue-400' : 'text-gray-400'}`} />
          )}

          {/* Dropdown Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                onClick={(e) => e.stopPropagation()}
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-opacity ${isActive ? 'opacity-100 hover:bg-blue-200/50 dark:hover:bg-blue-800/50' : 'opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-700'} data-[state=open]:opacity-100`}
              >
                <MoreVertical size={16} className={isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              sideOffset={5}
              className="w-48 rounded-2xl bg-gray-900/95 backdrop-blur-xl border border-gray-700/50 shadow-2xl p-1.5"
            >
              {/* Pin Option */}
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  if (onPin) onPin(conversation.id);
                }}
                className="px-3 py-2.5 text-sm font-medium text-gray-200 hover:bg-white/10 dark:hover:bg-white/10 hover:text-white rounded-xl flex items-center gap-3 cursor-pointer focus:bg-white/10 dark:focus:bg-white/10 focus:text-white transition-colors"
              >
                <Pin size={16} className="text-blue-400" />
                <span>{conversation.isPinned ? 'Bỏ ghim' : 'Ghim'}</span>
              </DropdownMenuItem>

              {/* Rename Option */}
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onRenameStart();
                }}
                className="px-3 py-2.5 text-sm font-medium text-gray-200 hover:bg-white/10 dark:hover:bg-white/10 hover:text-white rounded-xl flex items-center gap-3 cursor-pointer focus:bg-white/10 dark:focus:bg-white/10 focus:text-white transition-colors"
              >
                <Edit3 size={16} className="text-gray-400" />
                <span>Đổi tên</span>
              </DropdownMenuItem>

              {/* Delete Option */}
              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(conversation.id);
                }}
                className="px-3 py-2.5 text-sm font-medium text-red-400 hover:bg-red-500/20 dark:hover:bg-red-500/20 hover:text-red-300 rounded-xl flex items-center gap-3 cursor-pointer focus:bg-red-500/20 dark:focus:bg-red-500/20 focus:text-red-300 transition-colors"
              >
                <Trash2 size={16} />
                <span>Xóa</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </motion.div>
  );
}

export function ConversationSidebar({
  conversations,
  activeConversationId,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onPinConversation,
  onRenameConversation,
  isDarkMode,
  isOpen,
  onToggle,
}: ConversationSidebarProps) {
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const handleRename = (id: string) => {
    if (onRenameConversation && renameValue.trim()) {
      onRenameConversation(id, renameValue.trim());
    }
    setRenamingId(null);
    setRenameValue('');
  };

  return (
    <>
      {/* Mobile Toggle Button */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={onToggle}
        className="lg:hidden fixed top-6 left-4 z-50 w-10 h-10 rounded-2xl backdrop-blur-2xl bg-white/80 dark:bg-gray-800/80 border border-white/50 dark:border-gray-700/50 shadow-xl flex items-center justify-center"
      >
        {isOpen ? <ChevronLeft size={20} /> : <Menu size={20} />}
      </motion.button>

      {/* Backdrop for Mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onToggle}
            className="lg:hidden fixed inset-0 bg-black/40 backdrop-blur-sm z-30"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.div
        initial={{ x: -320 }}
        animate={{ x: isOpen ? 0 : -320 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="fixed lg:relative top-0 left-0 h-full z-40 lg:z-0 flex flex-col flex-shrink-0"
        style={{ width: '20rem', minWidth: '20rem', maxWidth: '20rem' }}
      >
        {/* Glass Container */}
        <div className="h-full backdrop-blur-2xl bg-white/70 dark:bg-gray-900/70 border-r border-white/50 dark:border-gray-700/50 shadow-2xl relative overflow-hidden">
          {/* Animated Background Orb */}
          <motion.div
            animate={{
              x: [0, 50, 0],
              y: [0, -50, 0],
              scale: [1, 1.2, 1],
            }}
            transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
            className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-blue-400/20 to-cyan-400/20 dark:from-blue-500/10 dark:to-cyan-500/10 rounded-full blur-3xl pointer-events-none"
          />

          <div className="relative z-10 h-full flex flex-col p-4">
            {/* New Conversation Button */}
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button
                  onClick={onNewConversation}
                  className="w-full h-auto py-3 rounded-lg bg-gradient-to-br from-blue-500 via-cyan-500 to-teal-500 hover:from-blue-600 hover:via-cyan-600 hover:to-teal-600 text-white border-0 shadow-xl shadow-blue-500/30 relative overflow-hidden group"
                >
                  {/* Shimmer Effect */}
                  <motion.div
                    animate={{ x: ['-100%', '200%'] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                  />

                  <div className="relative z-10 flex items-center justify-center gap-2">
                    <Plus size={20} />
                    <span>Cuộc trò chuyện mới</span>
                  </div>
                </Button>
              </motion.div>
            </motion.div>

            {/* Conversations List */}
            <div className="flex-1 mt-4 overflow-hidden">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="mb-3"
              >
                <h3 className="text-sm text-gray-600 dark:text-gray-400 px-2">
                  Lịch sử trò chuyện
                </h3>
              </motion.div>

              <ScrollArea className="h-[calc(100%-2rem)] w-full overflow-x-hidden">
                <div className="space-y-1.5 pr-2 w-full">
                  <AnimatePresence mode="popLayout">
                    {conversations.length === 0 ? (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-center py-8 px-4"
                      >
                        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-800 mx-auto mb-3 flex items-center justify-center">
                          <MessageSquare size={24} className="text-gray-400 dark:text-gray-500" />
                        </div>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Chưa có cuộc trò chuyện nào
                        </p>
                      </motion.div>
                    ) : (
                      <>
                        {/* Pinned Conversations */}
                        {conversations.some(c => c.isPinned) && (
                          <div className="mb-6">
                            <h3 className="text-xs font-medium text-blue-500 dark:text-cyan-400 px-4 mb-2 uppercase tracking-wider">
                              Đã ghim
                            </h3>
                            {conversations.filter(c => c.isPinned).map((conversation, index) => (
                              <SidebarItem
                                key={conversation.id}
                                conversation={conversation}
                                isActive={activeConversationId === conversation.id}
                                onSelect={() => onSelectConversation(conversation.id)}
                                onRename={onRenameConversation ? (id, title) => onRenameConversation(id, title) : undefined}
                                onPin={onPinConversation ? (id) => onPinConversation(id) : undefined}
                                onDelete={(id) => onDeleteConversation(id)}
                                isRenaming={renamingId === conversation.id}
                                onRenameStart={() => {
                                  setRenamingId(conversation.id);
                                  setRenameValue(conversation.title);
                                }}
                                onRenameCancel={() => {
                                  setRenamingId(null);
                                  setRenameValue('');
                                }}
                                renameValue={renameValue}
                                setRenameValue={setRenameValue}
                                index={index}
                              />
                            ))}
                          </div>
                        )}

                        {/* Recent Conversations */}
                        <div>
                          {conversations.some(c => c.isPinned) && (
                            <h3 className="text-xs font-medium text-gray-500 dark:text-gray-500 px-4 mb-2 uppercase tracking-wider">
                              Gần đây
                            </h3>
                          )}
                          {conversations.filter(c => !c.isPinned).map((conversation, index) => (
                            <SidebarItem
                              key={conversation.id}
                              conversation={conversation}
                              isActive={activeConversationId === conversation.id}
                              onSelect={() => onSelectConversation(conversation.id)}
                              onRename={onRenameConversation ? (id, title) => onRenameConversation(id, title) : undefined}
                              onPin={onPinConversation ? (id) => onPinConversation(id) : undefined}
                              onDelete={(id) => onDeleteConversation(id)}
                              isRenaming={renamingId === conversation.id}
                              onRenameStart={() => {
                                setRenamingId(conversation.id);
                                setRenameValue(conversation.title);
                              }}
                              onRenameCancel={() => {
                                setRenamingId(null);
                                setRenameValue('');
                              }}
                              renameValue={renameValue}
                              setRenameValue={setRenameValue}
                              index={index}
                            />
                          ))}
                        </div>
                      </>
                    )}
                  </AnimatePresence>
                </div>
              </ScrollArea>
            </div>

            {/* Bottom Info */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="mt-4 pt-4 border-t border-white/50 dark:border-gray-700/50"
            >
              <div className="px-2 py-3 rounded-2xl backdrop-blur-xl bg-gradient-to-br from-blue-500/10 via-cyan-500/10 to-transparent border border-blue-200/30 dark:border-blue-700/30">
                <p className="text-xs text-gray-600 dark:text-gray-400 text-center">
                  🤖 Trợ lý AI Đề cương
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500 text-center mt-1">
                  Powered by AI
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </>
  );
}
