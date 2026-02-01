import { motion } from 'motion/react';
import { Sun, Moon } from 'lucide-react';

interface DarkModeToggleProps {
  isDark: boolean;
  onToggle: () => void;
}

export function DarkModeToggle({ isDark, onToggle }: DarkModeToggleProps) {
  return (
    <motion.button
      onClick={onToggle}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className="relative w-16 h-8 rounded-full p-1 backdrop-blur-xl border transition-all duration-500 overflow-hidden bg-gradient-to-br from-white/60 to-white/40 dark:from-gray-800/60 dark:to-gray-700/60 border-gray-300/50 dark:border-gray-600/50 shadow-lg"
    >
      {/* Animated Background */}
      <motion.div
        animate={{
          background: isDark
            ? 'linear-gradient(135deg, rgba(59,130,246,0.3), rgba(147,51,234,0.3))'
            : 'linear-gradient(135deg, rgba(251,191,36,0.3), rgba(249,115,22,0.3))',
        }}
        transition={{ duration: 0.5 }}
        className="absolute inset-0"
      />

      {/* Toggle Circle */}
      <motion.div
        animate={{
          x: isDark ? 32 : 0,
        }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        className="relative w-6 h-6 rounded-full bg-gradient-to-br from-white to-gray-100 dark:from-gray-900 dark:to-gray-800 shadow-lg flex items-center justify-center"
      >
        <motion.div
          initial={false}
          animate={{ rotate: isDark ? 360 : 0 }}
          transition={{ duration: 0.5 }}
        >
          {isDark ? (
            <Moon size={14} className="text-blue-400" />
          ) : (
            <Sun size={14} className="text-orange-500" />
          )}
        </motion.div>
      </motion.div>

      {/* Decorative Stars (Dark Mode) */}
      {isDark && (
        <>
          <motion.div
            animate={{ opacity: [0, 1, 0], scale: [0, 1, 0] }}
            transition={{ duration: 2, repeat: Infinity, delay: 0 }}
            className="absolute top-2 left-2 w-1 h-1 bg-blue-300 rounded-full"
          />
          <motion.div
            animate={{ opacity: [0, 1, 0], scale: [0, 1, 0] }}
            transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
            className="absolute top-4 left-4 w-0.5 h-0.5 bg-purple-300 rounded-full"
          />
        </>
      )}
    </motion.button>
  );
}
