import { motion } from 'motion/react';
import { Sparkles, Zap, TrendingUp } from 'lucide-react';

// 🎨 HƯỚNG DẪN TỰY CHỈNH:
// 1. Thêm/bớt câu hỏi mẫu: Chỉnh sửa mảng 'quickQuestions' bên dưới
// 2. Thay đổi icon: Import icon mới từ 'lucide-react' và thay thế
// 3. Thay đổi màu: Sửa gradient colors trong className

interface QuickActionsProps {
  onSelectQuestion: (question: string) => void;
  isDarkMode: boolean;
}

export function QuickActions({ onSelectQuestion, isDarkMode }: QuickActionsProps) {
  // 📝 DANH SÁCH CÂU HỎI MẪU - THÊM/BỚT TẠI ĐÂY
  const quickQuestions = [
    {
      icon: Zap,
      text: 'Cách tính điểm môn Toán rời rạc 1A?',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      icon: TrendingUp,
      text: 'Mục tiêu học phần Cơ học lý thuyết?',
      color: 'from-purple-500 to-pink-500',
    },
    {
      icon: Sparkles,
      text: 'Giảng viên môn Giải tích 1A là ai?',
      color: 'from-orange-500 to-red-500',
    },
    {
      icon: Sparkles,
      text: 'Tài liệu tham khảo môn Đại số tuyến tính?',
      color: 'from-green-500 to-teal-500',
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.8, duration: 0.5 }}
      className="mt-6"
    >
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 text-center">
        💡 Hoặc thử các câu hỏi mẫu:
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {quickQuestions.map((question, index) => {
          const Icon = question.icon;

          return (
            <motion.button
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.9 + index * 0.1 }}
              whileHover={{ scale: 1.03, y: -2 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => onSelectQuestion(question.text)}
              className="group relative overflow-hidden rounded-2xl backdrop-blur-xl bg-white/60 dark:bg-gray-800/60 hover:bg-white/80 dark:hover:bg-gray-800/80 border border-white/50 dark:border-gray-700/50 p-4 text-left transition-all duration-300 shadow-lg hover:shadow-xl"
            >
              {/* Gradient Hover Effect */}
              <motion.div
                initial={{ opacity: 0 }}
                whileHover={{ opacity: 1 }}
                className={`absolute inset-0 bg-gradient-to-br ${question.color} opacity-0 group-hover:opacity-10 transition-opacity duration-300`}
              />

              <div className="relative z-10 flex items-start gap-3">
                <div
                  className={`w-8 h-8 rounded-xl bg-gradient-to-br ${question.color} flex items-center justify-center flex-shrink-0 shadow-lg group-hover:scale-110 transition-transform duration-300`}
                >
                  <Icon size={16} className="text-white" />
                </div>
                <p className="flex-1 text-sm text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                  {question.text}
                </p>
              </div>
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
}
