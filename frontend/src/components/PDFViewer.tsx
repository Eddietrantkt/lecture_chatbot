import { motion, AnimatePresence } from 'motion/react';
import { X, FileText, ExternalLink } from 'lucide-react';
import { Button } from './ui/button';
import { useState, useEffect } from 'react';

interface PDFViewerProps {
  isOpen: boolean;
  url: string;
  title: string;
  articleNum?: string;
  pageNum?: number;
  onClose: () => void;
}

export function PDFViewer({ isOpen, url, title, articleNum, pageNum, onClose }: PDFViewerProps) {
  const [pdfUrlState, setPdfUrlState] = useState('');
  const [pdfLoaded, setPdfLoaded] = useState(false);

  // ✅ Fetch page number from backend if missing
  useEffect(() => {
    const fetchPageNumber = async () => {
      if (isOpen && articleNum && (!pageNum || pageNum === 0)) {
        try {
          // Extract domain_id from URL: /api/pdf-file/{domain_id}/{filename}
          const match = url.match(/\/api\/pdf-file\/([^\/]+)\//);
          const domainId = match ? match[1] : null;

          if (domainId) {
            console.log(`[PDFViewer] Fetching page for Article ${articleNum} in domain ${domainId}...`);
            const res = await fetch(`http://localhost:7860/api/pdf/find-page/${domainId}/${articleNum}`);
            const data = await res.json();

            if (data.found && data.page) {
              console.log(`[PDFViewer] Found Article ${articleNum} on page ${data.page}`);
              // Force reload with new page
              const timestamp = Date.now();
              const separator = url.includes('?') ? '&' : '?';
              const newUrl = `${url}${separator}_t=${timestamp}#page=${data.page}`;
              setPdfUrlState(newUrl);
              return;
            }
          }
        } catch (err) {
          console.error('[PDFViewer] Error fetching page:', err);
        }
      }

      // Fallback: Use default URL construction
      const targetPage = pageNum && pageNum > 0 ? pageNum : 1;
      const timestamp = Date.now();
      const separator = url.includes('?') ? '&' : '?';
      const searchParam = articleNum ? `&search="Điều ${articleNum}"` : '';
      const newUrl = `${url}${separator}_t=${timestamp}#page=${targetPage}${searchParam}`;
      setPdfUrlState(newUrl);
    };

    if (isOpen) {
      fetchPageNumber();
    }
  }, [isOpen, url, articleNum, pageNum]);

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
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed inset-4 md:inset-8 z-50 flex flex-col overflow-hidden rounded-3xl backdrop-blur-2xl bg-white/95 dark:bg-gray-900/95 border border-gray-200/50 dark:border-gray-700/50 shadow-2xl"
          >
            {/* Header with Glass Effect */}
            <div className="flex-shrink-0 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-cyan-500/10 to-teal-500/10 dark:from-blue-500/5 dark:via-cyan-500/5 dark:to-teal-500/5" />

              <div className="relative z-10 p-6 border-b border-gray-200/50 dark:border-gray-700/50">
                {/* Tiêu đề và nút đóng */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-500 via-cyan-500 to-teal-500 flex items-center justify-center shadow-lg">
                      <FileText size={20} className="text-white" />
                    </div>
                    <div>
                      <h2 className="font-semibold text-gray-900 dark:text-gray-100">
                        {title}
                      </h2>
                      {articleNum && (
                        <p className="text-sm text-blue-600 dark:text-cyan-400 font-medium">
                          📍 Điều {articleNum}
                        </p>
                      )}
                    </div>
                  </div>

                  <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                    <Button
                      onClick={onClose}
                      variant="ghost"
                      className="w-10 h-10 p-0 rounded-2xl hover:bg-gray-200/50 dark:hover:bg-gray-800/50"
                    >
                      <X size={20} />
                    </Button>
                  </motion.div>
                </div>

                {/* Article info */}
                {articleNum && (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-500/10 dark:bg-blue-500/5 border border-blue-500/30 dark:border-blue-500/20">
                    <FileText size={16} className="text-blue-600 dark:text-cyan-400" />
                    <span className="text-sm text-blue-600 dark:text-cyan-400 font-medium">
                      📄 Xem Điều {articleNum}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* PDF Content */}
            <div className="flex-1 overflow-hidden bg-gray-100 dark:bg-gray-950">
              {/* ✅ Use iframe for better search support */}
              <iframe
                src={pdfUrlState}
                className="w-full h-full border-0"
                title={title}
              />

              {/* ✅ Open in new tab button */}
              <div className="absolute bottom-4 right-4 z-10">
                <Button
                  onClick={() => window.open(pdfUrlState, '_blank')}
                  className="gap-2 bg-blue-600 hover:bg-blue-700 shadow-lg"
                  size="sm"
                >
                  <ExternalLink size={16} />
                  Mở ở tab mới
                </Button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
