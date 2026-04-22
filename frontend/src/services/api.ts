/**
 * API Service - Connect to FastAPI Backend
 */
import { getApiBase } from '../config/api';

const API_BASE = getApiBase();
console.log('[API] API_BASE initialized:', API_BASE);

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface QuestionRequest {
  question: string;
  session_id: string;
  use_advanced: boolean;
  model_mode: 'summary' | 'detail';
  chat_history: ChatMessage[];
  previous_context?: string;
}

export interface ClarifyRequest {
  session_id: string;
  selected_code: string;
  original_question: string;
}

export interface PDFSource {
  pdf_file: string;
  page_num?: number;
  content: string;
  highlight_text: string;
  json_file?: string;
  article_num?: string;
}

export interface TimingInfo {
  total_ms: number;
  search_ms: number;
  generation_ms: number;
  status: string;
}

export interface AnswerResponse {
  answer: string;
  sources: Array<{
    source: string;
    content: string;
  }>;
  pdf_sources: PDFSource[];
  search_mode?: string;
  search_method?: string;
  timing?: TimingInfo;
  timing_ms?: number;
  candidates?: Array<{ code: string; name: string }>;
  need_clarification?: boolean;
  selected_subject?: string;
}
export interface FeedbackRequest {
  query: string;
  answer: string;
  context: Array<{ source: string; content: string }>;
  status: 'like' | 'dislike';
  comment?: string;
}

export interface StatsResponse {
  total_chunks: number;
  laws: Record<string, number>;
  models: {
    embedder: string;
    llm_full: string;
    llm_lite: string;
  };
  intent_cache_size: number;
}

/**
 * Send question to backend
 */
export async function askQuestion(
  question: string,
  sessionId: string,
  mode: 'summary' | 'detail' = 'detail',
  chatHistory: ChatMessage[] = [],
  previousContext?: string
): Promise<AnswerResponse> {
  const response = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      session_id: sessionId,
      use_advanced: true,
      model_mode: mode,
      chat_history: chatHistory,
      previous_context: previousContext,
    } as QuestionRequest),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Resolve an ambiguous course/major candidate selection.
 */
export async function clarifySubject(
  sessionId: string,
  selectedCode: string,
  originalQuestion: string
): Promise<AnswerResponse> {
  const response = await fetch(`${API_BASE}/clarify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      selected_code: selectedCode,
      original_question: originalQuestion,
    } as ClarifyRequest),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Get suggested follow-up questions
 */
export async function suggestQuestions(
  question: string,
  answer: string,
  maxQuestions: number = 3
): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE}/suggest-questions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        answer,
        max_questions: maxQuestions,
      }),
    });

    if (!response.ok) {
      console.error('[API] Failed to get suggestions:', response.status);
      return [];
    }

    const data = await response.json();
    return data.questions || [];
  } catch (error) {
    console.error('[API] Error getting suggestions:', error);
    return [];
  }
}

/**
 * Submit feedback
 */
export async function submitFeedback(
  query: string,
  answer: string,
  context: Array<{ source: string; content: string }>,
  status: 'like' | 'dislike',
  comment?: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      answer,
      context,
      status,
      comment,
    } as FeedbackRequest),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Get system statistics
 */
export async function getStats(): Promise<StatsResponse> {
  const response = await fetch(`${API_BASE}/stats`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Get PDF document (base64)
 */
export async function getDocument(filename: string): Promise<{ filename: string; data: string }> {
  console.log('[API] getDocument called with:', filename);

  const domainMap: Record<string, string> = {
    'luat_hon_nhan.pdf': 'hon_nhan',
    'luat_hinh_su.pdf': 'hinh_su',
    'luat_lao_dong.pdf': 'lao_dong',
    'luat_dat_dai.pdf': 'dat_dai',
    'luat_dau_thau.pdf': 'dau_thau',
    'luat_chuyen_giao_cong_nghe.pdf': 'chuyen_giao_cong_nghe',
    'nghi_dinh_214_2025.pdf': 'nghi_dinh_214',
  };

  let domain_id = 'hon_nhan';
  for (const [pdf, domain] of Object.entries(domainMap)) {
    if (filename.includes(pdf)) {
      domain_id = domain;
      break;
    }
  }

  console.log('[API] Parsed:', { domain_id, filename });

  const url = `${API_BASE}/api/pdf-file/${domain_id}/${filename}`;
  console.log('[API] Fetching from:', url);

  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Accept': 'application/pdf' },
  });

  if (!response.ok) {
    console.error('[API] HTTP error:', response.status, response.statusText);
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const blob = await response.blob();
  const reader = new FileReader();

  return new Promise((resolve, reject) => {
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(',')[1];
      console.log('[API] PDF loaded, size:', blob.size, 'bytes');
      resolve({ filename, data: base64 });
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Build PDF URL from backend.
 */
export function getPDFUrl(pdfFile: string): string {
  const baseFilename = pdfFile.replace(/\([^)]*\)/, '').replace('.pdf', '');

  const domainMap: Record<string, string> = {
    'luat_hon_nhan': 'hon_nhan',
    'luat_hinh_su': 'hinh_su',
    'luat_lao_dong': 'lao_dong',
    'luat_dat_dai': 'dat_dai',
    'luat_dau_thau': 'dau_thau',
    'luat_chuyen_giao_cong_nghe': 'chuyen_giao_cong_nghe',
    'nghi_dinh_214_2025': 'dau_thau',
    'luat_so_huu_tri_tue': 'lshtt',
  };

  const domain_id = domainMap[baseFilename] || 'hon_nhan';

  console.log('[API] getPDFUrl:', {
    pdfFile,
    baseFilename,
    domain_id
  });

  const pdfUrl = `${API_BASE}/api/pdf-file/${domain_id}/${pdfFile}`;
  console.log('[API] getPDFUrl:', { pdfFile, domain_id, pdfUrl });
  return pdfUrl;
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{
  status: string;
  models_loaded: boolean;
  total_chunks: number;
}> {
  const response = await fetch(`${API_BASE}/health`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}
