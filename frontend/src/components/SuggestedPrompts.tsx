import { motion } from 'motion/react';
import { MessageSquare, BookOpen, Scale, FileText } from 'lucide-react';

// 🎨 HƯỚNG DẪN TỰY CHỈNH:
// 1. Thêm/bớt gợi ý: Chỉnh sửa mảng 'prompts' bên dưới
// 2. Thay đổi icon: Import icon mới từ 'lucide-react'
// 3. Thay đổi màu: Sửa gradient trong className

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string) => void;
}

export function SuggestedPrompts({ onSelectPrompt }: SuggestedPromptsProps) {
  // 📝 DANH SÁCH GỢI Ý - THÊM/BỚT TẠI ĐÂY
  const prompts = [
    {
      icon: Scale,
      text: 'Độ tuổi hợp pháp để kết hôn tại Việt Nam là bao nhiêu?',
    },
    {
      icon: FileText,
      text: 'Quyền lợi pháp lý trong quá trình ly hôn là gì?',
    },
    {
      icon: BookOpen,
      text: 'Quyền sở hữu trí tuệ theo luật Việt Nam như thế nào?',
    },
    {
      icon: MessageSquare,
      text: 'Quyền lợi người lao động',
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-wrap gap-1.5 justify-center"
    >
      {prompts.map((prompt, index) => {
        const Icon = prompt.icon;
        
        return (
          <motion.button
            key={index}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05 }}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onSelectPrompt(prompt.text)}
            className="group flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg backdrop-blur-xl bg-white/60 dark:bg-gray-800/60 hover:bg-white/80 dark:hover:bg-gray-800/80 border border-white/50 dark:border-gray-700/50 text-xs text-gray-700 dark:text-gray-300 transition-all duration-200 shadow-sm hover:shadow-md"
          >
            <Icon size={12} className="text-blue-500 dark:text-cyan-400 flex-shrink-0" />
            <span className="whitespace-nowrap">{prompt.text}</span>
          </motion.button>
        );
      })}
    </motion.div>
  );
}

