import { motion } from 'motion/react';

// Component hiển thị sources dạng hyperlink theo từng điều luật
// Mỗi điều luật là 1 link riêng, compact và đẹp mắt

interface Source {
  title: string;
  page?: string;
  pdfUrl?: string;
  articleNum?: string;
}

interface SourceLinksProps {
  sources: Source[];
  onOpenPDF: (url: string, title: string, articleNum?: string) => void;
}

export function SourceLinks({ sources, onOpenPDF }: SourceLinksProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="ml-14 mt-3 flex flex-wrap gap-2"
    >
      {sources.map((source, idx) => {
        return (
          <motion.a
            key={idx}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 * idx }}
            href={source.pdfUrl || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center gap-2 px-3 py-2 rounded-xl backdrop-blur-xl bg-blue-500/10 dark:bg-blue-500/5 hover:bg-blue-500/20 dark:hover:bg-blue-500/10 border border-blue-500/30 dark:border-blue-500/20 transition-all duration-300 hover:scale-105 hover:shadow-lg"
          >
            {/* Số thứ tự */}
            <div className="w-5 h-5 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 text-white flex items-center justify-center text-xs font-medium shadow-md group-hover:scale-110 transition-transform">
              {idx + 1}
            </div>

            {/* Tên luật và điều */}
            <div className="flex flex-col">
              <span className="text-xs font-medium text-blue-600 dark:text-cyan-400 group-hover:underline">
                {source.title}
              </span>
              {source.page && (
                <span className="text-xs text-blue-500 dark:text-cyan-500">
                  {source.page}
                </span>
              )}
            </div>
          </motion.a>
        );
      })}
    </motion.div>
  );
}
