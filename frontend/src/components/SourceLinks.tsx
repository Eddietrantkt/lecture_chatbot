import { motion } from 'motion/react';
import { FileText, ExternalLink } from 'lucide-react';
import { getPDFUrl } from '../services/api';

// Component hiển thị sources dạng hyperlink theo từng điều luật
// ✅ Mỗi điều luật là 1 link có thể click
// ✅ Khi click sẽ mở PDF viewer và tự động scroll đến điều đó
// ✅ Có icon PDF để dễ nhận biết
// ✅ Load PDF từ backend API

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

  const handleSourceClick = (e: React.MouseEvent, source: Source) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (source.pdfUrl) {
      const articleNum = source.articleNum || source.page?.replace('Điều ', '') || '';
      // ✅ Build PDF URL từ backend
      const pdfUrl = getPDFUrl(source.pdfUrl);
      console.log('[SourceLinks] Opening PDF:', { source, pdfUrl, articleNum });
      // Gọi callback để mở PDF viewer với điều luật cụ thể
      onOpenPDF(pdfUrl, source.title, articleNum);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="ml-14 mt-3 flex flex-wrap gap-2"
    >
      {sources.map((source, idx) => (
        <motion.button
          key={idx}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 * idx }}
          onClick={(e) => handleSourceClick(e, source)}
          className="group relative inline-flex items-center gap-2 px-3 py-2 rounded-xl backdrop-blur-xl bg-blue-500/10 dark:bg-blue-500/5 hover:bg-blue-500/20 dark:hover:bg-blue-500/10 border border-blue-500/30 dark:border-blue-500/20 transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-blue-500/25 cursor-pointer overflow-hidden"
          aria-label={`Mở ${source.title}`}
        >
          {/* Animated Background on Hover */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-blue-400/0 via-cyan-400/0 to-blue-400/0"
            whileHover={{
              background: 'linear-gradient(90deg, rgba(96, 165, 250, 0.1), rgba(34, 211, 238, 0.1), rgba(96, 165, 250, 0.1))',
            }}
            transition={{ duration: 0.3 }}
          />

          {/* Icon PDF */}
          <motion.div
            className="relative w-5 h-5 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 text-white flex items-center justify-center text-xs font-medium shadow-md flex-shrink-0"
            whileHover={{ scale: 1.15, rotate: 10 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            <FileText size={14} />
          </motion.div>

          {/* Tên luật và điều */}
          <div className="relative flex flex-col">
            <span className="text-xs font-medium text-blue-600 dark:text-cyan-400 group-hover:underline transition-all">
              {source.title}
            </span>
            {source.page && (
              <span className="text-xs text-blue-500 dark:text-cyan-500 font-medium">
                {source.page}
              </span>
            )}
          </div>

          {/* External Link Icon - hiển thị khi hover */}
          <motion.div
            className="relative ml-1 opacity-0"
            whileHover={{ opacity: 1, x: 2 }}
            transition={{ duration: 0.2 }}
          >
            <ExternalLink size={12} className="text-blue-500 dark:text-cyan-400" />
          </motion.div>
        </motion.button>
      ))}
    </motion.div>
  );
}
