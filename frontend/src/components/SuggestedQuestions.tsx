import { useState, MouseEvent } from 'react';
import { X, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { Button } from './ui/button';

interface SuggestedQuestionsProps {
  questions: string[];
  onSelectQuestion: (question: string) => void;
  onClear: () => void;
  isDarkMode: boolean;
}

export function SuggestedQuestions({ questions, onSelectQuestion, onClear, isDarkMode }: SuggestedQuestionsProps) {
  const [isExpanded, setIsExpanded] = useState(true);  // Start expanded, user can collapse

  if (!questions || questions.length === 0) return null;

  // Show only the first 2 suggested questions
  const displayQuestions = questions.slice(0, 2);

  return (
    <div
      className={`rounded-lg overflow-hidden transition-all duration-300 ease-in-out ${isDarkMode
          ? 'bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-blue-800/30'
          : 'bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200'
        }`}
      style={{
        maxHeight: isExpanded ? '400px' : '48px',
        opacity: 1,
        transform: 'scale(1)'
      }}
    >
      <div
        className="flex items-center justify-between p-3 cursor-pointer hover:opacity-80 transition-opacity"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Sparkles size={18} className="text-blue-500" />
          <span className={`text-sm font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {isExpanded ? 'Gợi ý câu hỏi tiếp theo' : `Xem gợi ý 2 câu hỏi tiếp theo`}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {isExpanded ? (
            <ChevronUp size={18} className={isDarkMode ? 'text-gray-400' : 'text-gray-500'} />
          ) : (
            <ChevronDown size={18} className={isDarkMode ? 'text-gray-400' : 'text-gray-500'} />
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={(e: MouseEvent) => {
              e.stopPropagation();
              onClear();
            }}
            className="h-6 w-6 p-0 hover:bg-gray-200 dark:hover:bg-gray-700 ml-1"
          >
            <X size={16} className={isDarkMode ? 'text-gray-400' : 'text-gray-500'} />
          </Button>
        </div>
      </div>

      {isExpanded && (
        <div className="px-3 pb-3 space-y-2 transition-all duration-200 ease-in-out">
          {displayQuestions.map((question, index) => {
            // Extract question text (remove emoji if present)
            const cleanQuestion = question.replace(/^💭\s*/, '').trim();

            return (
              <button
                key={index}
                onClick={() => onSelectQuestion(cleanQuestion)}
                className={`w-full text-left p-3 rounded-md text-sm transition-all ${isDarkMode
                    ? 'bg-gray-800/50 hover:bg-gray-700 text-gray-200 hover:border-blue-500'
                    : 'bg-white hover:bg-blue-50 text-gray-800 hover:border-blue-400'
                  } border border-transparent hover:shadow-md`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5">💭</span>
                  <span className="flex-1 leading-relaxed">{cleanQuestion}</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
