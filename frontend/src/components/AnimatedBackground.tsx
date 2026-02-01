import { motion } from 'motion/react';

export function AnimatedBackground() {
    return (
        <div className="fixed inset-0 bg-gradient-to-br from-blue-50 via-cyan-50 to-teal-50 dark:from-gray-950 dark:via-blue-950 dark:to-purple-950 -z-10">
            {/* Floating Orbs */}
            <motion.div
                animate={{
                    x: [0, 100, 0],
                    y: [0, -100, 0],
                    scale: [1, 1.2, 1],
                }}
                transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                className="absolute top-20 left-20 w-96 h-96 bg-gradient-to-br from-blue-400/30 to-cyan-400/30 dark:from-blue-500/20 dark:to-cyan-500/20 rounded-full blur-3xl opacity-50 block"
            />
            <motion.div
                animate={{
                    x: [0, -100, 0],
                    y: [0, 100, 0],
                    scale: [1, 1.3, 1],
                }}
                transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
                className="absolute bottom-20 right-20 w-[32rem] h-[32rem] bg-gradient-to-br from-purple-400/30 to-pink-400/30 dark:from-purple-500/20 dark:to-pink-500/20 rounded-full blur-3xl opacity-50 block"
            />
            <motion.div
                animate={{
                    x: [0, 50, 0],
                    y: [0, -50, 0],
                    scale: [1, 1.1, 1],
                }}
                transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
                className="absolute top-1/2 left-1/2 w-80 h-80 bg-gradient-to-br from-teal-400/30 to-green-400/30 dark:from-teal-500/20 dark:to-green-500/20 rounded-full blur-3xl opacity-50 block"
            />
        </div>
    );
}
