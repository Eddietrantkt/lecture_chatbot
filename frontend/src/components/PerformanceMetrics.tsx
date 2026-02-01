import { Clock, Zap, Database } from 'lucide-react';
import { Card } from './ui/card';

interface PerformanceMetricsProps {
  timing_ms?: number;
  search_method?: string;
  isDarkMode?: boolean;
}

export function PerformanceMetrics({ timing_ms, search_method, isDarkMode }: PerformanceMetricsProps) {
  if (!timing_ms) return null;

  const totalSeconds = (timing_ms / 1000).toFixed(2);
  const isfast = timing_ms < 2000;

  return (
    <Card className={`mt-3 p-3 border ${
      isDarkMode 
        ? 'bg-gray-800/50 border-gray-700' 
        : 'bg-gray-50 border-gray-200'
    }`}>
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <Clock size={14} className={isDarkMode ? 'text-blue-400' : 'text-blue-500'} />
          <span className={isDarkMode ? 'text-gray-300' : 'text-gray-700'}>
            <span className="font-semibold">{totalSeconds}s</span>
          </span>
        </div>

        {search_method && (
          <div className="flex items-center gap-2">
            <Database size={14} className={isDarkMode ? 'text-purple-400' : 'text-purple-500'} />
            <span className={isDarkMode ? 'text-gray-300' : 'text-gray-700'}>
              {search_method.replace('domain_based_', '').replace('_', ' ')}
            </span>
          </div>
        )}

        <div className={`ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full ${
          isfast 
            ? isDarkMode ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-700'
            : isDarkMode ? 'bg-orange-900/30 text-orange-400' : 'bg-orange-100 text-orange-700'
        }`}>
          <Zap size={12} />
          <span className="font-medium">{isfast ? 'Fast' : 'Normal'}</span>
        </div>
      </div>
    </Card>
  );
}
