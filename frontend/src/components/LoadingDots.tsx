import { motion } from 'motion/react';

// Component loading dots đẹp hơn cho typing indicator
export function LoadingDots() {
  return (
    <div className="flex gap-1.5">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          animate={{
            y: [0, -8, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: i * 0.15,
            ease: 'easeInOut',
          }}
          className="w-2.5 h-2.5 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500"
        />
      ))}
    </div>
  );
}
