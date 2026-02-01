import { useState } from 'react';
import { motion } from 'motion/react';
import { Scale, AlertCircle, Sparkles } from 'lucide-react';
import { QuickActions } from './QuickActions';
import { PromptGuideDialog } from './PromptGuideDialog';

// 🎨 HƯỚNG DẪN TỰY CHỈNH:
// 1. Thêm/bớt luật: Chỉnh sửa mảng 'laws' bên dưới
// 2. Thay đổi số cột: Sửa 'grid-cols-2' thành 'grid-cols-1' (1 cột) hoặc 'grid-cols-3' (3 cột)
// 3. Thay đổi màu chủ đề: Tìm 'from-blue-500' và đổi gradient
// 4. Sửa nội dung chào mừng: Chỉnh 'title' và 'description'

interface WelcomeScreenProps {
  isDarkMode: boolean;
  onSelectQuestion?: (question: string) => void;
}

export function WelcomeScreen({ isDarkMode, onSelectQuestion }: WelcomeScreenProps) {
  const [isGuideOpen, setIsGuideOpen] = useState(false);

  // 📝 DANH SÁCH MÔN HỌC CHÍNH - THÊM/BỚT TẠI ĐÂY
  const categories = [
    'Môn Cơ sở (Toán, Lý...)',
    'Môn Chuyên ngành',
    'Cơ học & Vật lý',
    'Toán tin & Ứng dụng',
    'Đại số & Giải tích',
    'Xác suất Thống kê',
  ];

  // ✏️ NỘI DUNG CHÀO MỪNG - CHỈNH SỬA TẠI ĐÂY
  const welcomeContent = {
    title: 'AI Đề cương Học phần',
    description:
      'Chào mừng bạn đến với Hệ thống Giải đáp Đề cương Học phần. Tôi có thể hỗ trợ bạn tra cứu thông tin về giảng viên, cách tính điểm, mục tiêu và tài liệu tham khảo cho các môn học.',
    warningTitle: '⚠️ Hệ thống đang trong giai đoạn thử nghiệm (POC).',
    warningDescription:
      'Dữ liệu được trích xuất từ các file đề cương hiện có. Vui lòng xác nhận lại với giảng viên hoặc phòng đào tạo nếu có các thay đổi mới nhất.',
    hintTitle: 'Gợi ý:',
    hintDescription:
      'Cách đặt câu hỏi để nhận được thông tin chính xác nhất.',
  };

  // Chia danh sách thành 2 cột
  const midPoint = Math.ceil(categories.length / 2);
  const leftColumn = categories.slice(0, midPoint);
  const rightColumn = categories.slice(midPoint);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
      className="max-w-4xl mx-auto px-6 py-8"
    >
      {/* Glass Container */}
      <div className="relative overflow-hidden rounded-3xl backdrop-blur-2xl bg-white/70 dark:bg-gray-800/70 border border-white/50 dark:border-gray-700/50 shadow-2xl">
        {/* Animated Background Gradient */}
        <motion.div
          animate={{
            background: [
              'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1))',
              'linear-gradient(225deg, rgba(6,182,212,0.1), rgba(59,130,246,0.1))',
              'linear-gradient(315deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1))',
            ],
          }}
          transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
          className="absolute inset-0 opacity-50"
        />

        <div className="relative z-10 p-8">
          {/* Header with Icon */}
          <div className="flex items-center gap-4 mb-6">
            <motion.div
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 via-cyan-500 to-teal-500 flex items-center justify-center shadow-xl shadow-blue-500/30 relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-white/20 backdrop-blur-sm" />
              <Scale size={32} className="text-white relative z-10" />
            </motion.div>

            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {welcomeContent.title}
              </h1>
              <motion.div
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="flex items-center gap-2 mt-1"
              >
                <Sparkles size={14} className="text-blue-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Trợ lý AI thông minh
                </span>
              </motion.div>
            </div>
          </div>

          {/* Description */}
          <p className="text-gray-700 dark:text-gray-300 mb-6">
            {welcomeContent.description}
          </p>

          {/* Laws Grid - ĐỔI grid-cols-2 THÀNH grid-cols-1 hoặc grid-cols-3 để thay đổi số cột */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Left Column */}
            <div className="space-y-2">
              {leftColumn.map((law, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500" />
                  <span>{law}</span>
                </motion.div>
              ))}
            </div>

            {/* Right Column */}
            <div className="space-y-2">
              {rightColumn.map((law, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: (index + leftColumn.length) * 0.03 }}
                  className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500" />
                  <span>{law}</span>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Summary */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-sm text-gray-600 dark:text-gray-400 mb-6"
          >
            Bạn có thể hỏi bất kỳ thông tin nào có trong đề cương. Hệ thống sẽ tự động tìm kiếm và trích xuất câu trả lời cho bạn.
          </motion.p>

          {/* Warning Box */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="mb-6 relative overflow-hidden rounded-2xl backdrop-blur-xl bg-orange-500/10 dark:bg-orange-500/5 border border-orange-500/30 dark:border-orange-500/20 p-4"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-orange-400/10 rounded-full blur-2xl" />

            <div className="relative z-10">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-orange-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <AlertCircle size={14} className="text-orange-600 dark:text-orange-400" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-orange-700 dark:text-orange-300 mb-2">
                    {welcomeContent.warningTitle}
                  </p>
                  <p className="text-xs text-orange-600 dark:text-orange-400">
                    {welcomeContent.warningDescription}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Hint Box */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="relative overflow-hidden rounded-2xl backdrop-blur-xl bg-blue-500/10 dark:bg-blue-500/5 border border-blue-500/30 dark:border-blue-500/20 p-4"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-400/10 rounded-full blur-2xl" />

            <div className="relative z-10">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Sparkles size={14} className="text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-1">
                    {welcomeContent.hintTitle}
                  </p>
                  <button
                    onClick={() => setIsGuideOpen(true)}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {welcomeContent.hintDescription} →
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Quick Action Suggestions */}
      {onSelectQuestion && (
        <QuickActions onSelectQuestion={onSelectQuestion} isDarkMode={isDarkMode} />
      )}

      {/* Prompt Guide Dialog */}
      <PromptGuideDialog
        isOpen={isGuideOpen}
        onClose={() => setIsGuideOpen(false)}
        isDarkMode={isDarkMode}
      />
    </motion.div>
  );
}
