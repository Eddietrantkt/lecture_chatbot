import { motion, AnimatePresence } from 'motion/react';
import { X, Lightbulb, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import { Button } from './ui/button';

// 🎨 HƯỚNG DẪN TỰY CHỈNH:
// 1. Thêm/bớt tips: Chỉnh sửa mảng 'promptingTips' bên dưới
// 2. Thay đổi ví dụ: Sửa mảng 'goodExamples' và 'badExamples'

interface PromptGuideDialogProps {
  isOpen: boolean;
  onClose: () => void;
  isDarkMode: boolean;
}

export function PromptGuideDialog({ isOpen, onClose, isDarkMode }: PromptGuideDialogProps) {
  // 📝 TIPS PROMPTING - THÊM/BỚT TẠI ĐÂY
  const promptingTips = [
    {
      icon: CheckCircle2,
      title: 'Cụ thể và rõ ràng',
      description: 'Đặt câu hỏi cụ thể về vấn đề pháp lý của bạn, đề cập lĩnh vực luật liên quan.',
    },
    {
      icon: Lightbulb,
      title: 'Cung cấp ngữ cảnh',
      description: 'Mô tả hoàn cảnh, thời gian, địa điểm để AI hiểu rõ hơn tình huống của bạn.',
    },
    {
      icon: Sparkles,
      title: 'Một câu hỏi mỗi lần',
      description: 'Tập trung vào một vấn đề chính để nhận được câu trả lời chi tiết và chính xác.',
    },
    {
      icon: AlertCircle,
      title: 'Tránh thông tin nhạy cảm',
      description: 'Không chia sẻ thông tin cá nhân, số CMND, số tài khoản, hoặc thông tin bí mật.',
    },
  ];

  // ✅ VÍ DỤ TỐT
  const goodExamples = [
    'Tôi muốn thành lập công ty TNHH tại TP.HCM năm 2024. Vốn điều lệ tối thiểu là bao nhiêu?',
    'Người lao động nghỉ thai sản được hưởng bao nhiêu % lương? Thời gian nghỉ là bao lâu theo Luật Lao động 2019?',
    'Tôi bị chấm dứt hợp đồng lao động trái luật. Tôi có quyền yêu cầu bồi thường không?',
  ];

  // ❌ VÍ DỤ CHƯA TỐT
  const badExamples = [
    'Tôi có thắc mắc về luật',
    'Cho tôi hỏi về lao động và thuế',
    'Làm sao để giải quyết vấn đề này?',
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
          />

          {/* Dialog */}
          <div className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="relative w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-3xl backdrop-blur-2xl bg-white/95 dark:bg-gray-900/95 border border-white/50 dark:border-gray-700/50 shadow-2xl pointer-events-auto"
            >
              {/* Header */}
              <div className="relative overflow-hidden border-b border-gray-200/50 dark:border-gray-700/50 p-6">
                <motion.div
                  animate={{
                    background: [
                      'linear-gradient(135deg, rgba(59,130,246,0.1), rgba(6,182,212,0.1))',
                      'linear-gradient(225deg, rgba(6,182,212,0.1), rgba(59,130,246,0.1))',
                    ],
                  }}
                  transition={{ duration: 5, repeat: Infinity }}
                  className="absolute inset-0"
                />

                <div className="relative z-10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
                      <Sparkles size={20} className="text-white" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                        Hướng dẫn Prompt hiệu quả
                      </h2>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Tối ưu câu hỏi để nhận câu trả lời tốt nhất
                      </p>
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onClose}
                    className="rounded-xl hover:bg-gray-200/50 dark:hover:bg-gray-700/50"
                  >
                    <X size={20} />
                  </Button>
                </div>
              </div>

              {/* Content */}
              <div className="overflow-y-auto max-h-[calc(85vh-80px)] p-6 space-y-6">
                {/* Tips Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {promptingTips.map((tip, index) => {
                    const Icon = tip.icon;
                    return (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="relative overflow-hidden rounded-2xl backdrop-blur-xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 dark:from-blue-500/5 dark:to-cyan-500/5 border border-blue-200/50 dark:border-blue-700/50 p-4"
                      >
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0 shadow-md">
                            <Icon size={16} className="text-white" />
                          </div>
                          <div className="flex-1">
                            <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
                              {tip.title}
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {tip.description}
                            </p>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>

                {/* Good Examples */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 size={18} className="text-green-500" />
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                      ✅ Ví dụ Prompt tốt
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {goodExamples.map((example, index) => (
                      <div
                        key={index}
                        className="rounded-2xl backdrop-blur-xl bg-green-500/10 dark:bg-green-500/5 border border-green-500/30 dark:border-green-500/20 p-3"
                      >
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          "{example}"
                        </p>
                      </div>
                    ))}
                  </div>
                </motion.div>

                {/* Bad Examples */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <AlertCircle size={18} className="text-orange-500" />
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                      ❌ Ví dụ Prompt chưa tốt
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {badExamples.map((example, index) => (
                      <div
                        key={index}
                        className="rounded-2xl backdrop-blur-xl bg-orange-500/10 dark:bg-orange-500/5 border border-orange-500/30 dark:border-orange-500/20 p-3"
                      >
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          "{example}"
                        </p>
                      </div>
                    ))}
                  </div>
                </motion.div>

                {/* Quick Tips */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.6 }}
                  className="rounded-2xl backdrop-blur-xl bg-blue-500/10 dark:bg-blue-500/5 border border-blue-500/30 dark:border-blue-500/20 p-4"
                >
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    <strong>💡 Mẹo:</strong> Sử dụng các từ khóa như "theo Luật...", "quy định năm...", 
                    "điều kiện", "thủ tục", "quyền lợi" để AI hiểu rõ hơn yêu cầu của bạn.
                  </p>
                </motion.div>
              </div>

              {/* Footer */}
              <div className="border-t border-gray-200/50 dark:border-gray-700/50 p-4 backdrop-blur-xl bg-white/50 dark:bg-gray-900/50">
                <Button
                  onClick={onClose}
                  className="w-full rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white border-0 shadow-lg"
                >
                  Đã hiểu
                </Button>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
