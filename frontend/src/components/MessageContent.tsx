import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText } from 'lucide-react';
import { getPDFUrl } from '../services/api';

/**
 * Component để render AI message text với Markdown và hyperlinks cho các Điều luật
 */

interface MessageContentProps {
  text: string;
  pdfSources?: Array<{
    json_file?: string;
    pdf_file?: string;
    article_num?: string;
    page_num?: number;
    domain_id?: string;
  }>;
  onOpenPDF?: (url: string, title: string, articleNum?: string, pageNum?: number) => void;
}

// Map json_file → domain_id (from domain_registry.json structure)
const jsonToDomainMap: Record<string, string> = {
  'luat_lao_dong_hopnhat.json': 'lao_dong',
  'luat_lao_donghopnhat.json': 'lao_dong',
  'luat_dauthau_hopnhat.json': 'dau_thau',
  'luat_dau_thau_hopnhat.json': 'dau_thau',
  'nghi_dinh_214_2025.json': 'dau_thau',
  'luat_dat_dai_hopnhat.json': 'dat_dai',
  'luat_hon_nhan_hopnhat.json': 'hon_nhan',
  'luat_hon_nhan.json': 'hon_nhan',
  'chuyen_giao_cong_nghe_hopnhat.json': 'chuyen_giao_cong_nghe',
  'luat_so_huu_tri_tue_hopnhat.json': 'lshtt',
  'luat_hinh_su_hopnhat.json': 'hinh_su',
};

// Map domain_id → display_name
const domainInfoMap: Record<string, { displayName: string }> = {
  'lao_dong': { displayName: 'Luật Lao động' },
  'dau_thau': { displayName: 'Luật Đấu thầu' },
  'dat_dai': { displayName: 'Luật Đất đai' },
  'hon_nhan': { displayName: 'Luật Hôn nhân và Gia đình' },
  'chuyen_giao_cong_nghe': { displayName: 'Luật Chuyển giao công nghệ' },
  'lshtt': { displayName: 'Bộ luật Sở hữu trí tuệ' },
  'hinh_su': { displayName: 'Bộ luật Hình sự' },
};

export function MessageContent({ text }: MessageContentProps) {
  // 1. CLEANUP: Basic formatting cleanup
  let cleanText = text
    .replace(/^\n+/, '')                    // Remove leading newlines
    .replace(/\n{3,}/g, '\n\n')             // Normalize 3+ newlines to 2
    .replace(/\*\*([^*]+)\*\*\n{2,}/g, '**$1**\n')  // Remove extra newlines after bold headers
    .trim();

  const markdownText = cleanText;

  // 3. CUSTOM RENDERER for links
  const components = {
    a: ({ href, children, ...props }: any) => {
      // Normal link
      return <a href={href} {...props} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>;
    },
    // Custom styling for other elements
    p: ({ children }: any) => <p className="mb-4 leading-relaxed last:mb-0">{children}</p>,
    ul: ({ children }: any) => <ul className="list-disc pl-5 mb-4 space-y-1">{children}</ul>,
    ol: ({ children }: any) => <ol className="list-decimal pl-5 mb-4 space-y-1">{children}</ol>,
    li: ({ children }: any) => <li className="leading-relaxed">{children}</li>,
    strong: ({ children }: any) => <strong className="font-bold text-gray-900 dark:text-gray-100">{children}</strong>,
    h1: ({ children }: any) => <h1 className="text-xl font-bold mb-2 mt-4">{children}</h1>,
    h2: ({ children }: any) => <h2 className="text-lg font-bold mb-2 mt-3">{children}</h2>,
    h3: ({ children }: any) => <h3 className="text-md font-bold mb-1 mt-2">{children}</h3>,
    blockquote: ({ children }: any) => <blockquote className="border-l-4 border-gray-300 pl-4 italic my-4 text-gray-600 dark:text-gray-400">{children}</blockquote>,
    // Table components
    table: ({ children }: any) => (
      <div className="overflow-x-auto my-4 rounded-lg shadow-md border border-gray-300 dark:border-gray-500">
        <table className="min-w-full divide-y divide-gray-300 dark:divide-gray-500">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }: any) => (
      <thead className="bg-gray-200 dark:bg-gray-700">
        {children}
      </thead>
    ),
    tbody: ({ children }: any) => (
      <tbody className="bg-white dark:bg-gray-900/60 divide-y divide-gray-300 dark:divide-gray-500">
        {children}
      </tbody>
    ),
    tr: ({ children }: any) => (
      <tr className="hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
        {children}
      </tr>
    ),
    th: ({ children }: any) => (
      <th className="px-6 py-3 text-left text-sm font-bold text-black dark:text-white uppercase tracking-wider border-r last:border-r-0 border-gray-300 dark:border-gray-500">
        {children}
      </th>
    ),
    td: ({ children }: any) => (
      <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap border-r last:border-r-0 border-gray-300 dark:border-gray-500">
        {children}
      </td>
    ),
  };

  return (
    <div className="markdown-content text-sm md:text-base text-gray-800 dark:text-gray-200" >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {markdownText}
      </ReactMarkdown>
    </div >
  );
}
