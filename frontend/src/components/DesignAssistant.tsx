/**
 * Design Assistant Panel
 * Friendly, non-blocking validation with helpful suggestions
 */
import React, { useCallback } from 'react';
import clsx from 'clsx';
import { useStore } from '../store';
import { ValidationIssue, Layout, LayoutElement } from '../types';
import { validateLayout } from '../api';

// Helper to check if color is light
const isLightColor = (hex: string): boolean => {
  const c = hex.replace('#', '');
  const r = parseInt(c.substr(0, 2), 16);
  const g = parseInt(c.substr(2, 2), 16);
  const b = parseInt(c.substr(4, 2), 16);
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  return brightness > 128;
};

interface SuggestionCardProps {
  issue: ValidationIssue;
  onFix?: () => void;
}

const SuggestionCard: React.FC<SuggestionCardProps> = ({ issue, onFix }) => {
  const isHard = issue.severity === 'hard';

  // Friendly icons based on issue type
  const getIcon = () => {
    if (issue.code.includes('SAFE_ZONE')) {
      return (
        <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        </div>
      );
    }
    if (issue.code.includes('CONTRAST') || issue.code.includes('COLOR')) {
      return (
        <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
          </svg>
        </div>
      );
    }
    if (issue.code.includes('FONT')) {
      return (
        <div className="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h8m-8 6h16" />
          </svg>
        </div>
      );
    }
    if (issue.code.includes('DRINKAWARE') || issue.code.includes('ALCOHOL')) {
      return (
        <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
      );
    }
    return (
      <div className={clsx(
        "w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0",
        isHard ? "bg-red-100" : "bg-yellow-100"
      )}>
        <svg className={clsx("w-5 h-5", isHard ? "text-red-600" : "text-yellow-600")} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    );
  };

  // Friendly message rewording
  const getFriendlyMessage = () => {
    const msg = issue.message;
    if (msg.includes('violation')) return msg.replace('violation', 'suggestion');
    if (msg.includes('error')) return msg.replace('error', 'tip');
    if (msg.includes('must')) return msg.replace('must', 'should');
    return msg;
  };

  return (
    <div className="flex gap-3 p-4 bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
      {getIcon()}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-700 leading-relaxed">
          {getFriendlyMessage()}
        </p>
        {issue.fix_suggestion && (
          <p className="text-xs text-gray-500 mt-1.5 flex items-center gap-1">
            <span className="text-primary-500">💡</span>
            {issue.fix_suggestion}
          </p>
        )}
      </div>
      {issue.fix_suggestion && onFix && (
        <button
          onClick={onFix}
          className="px-3 py-1.5 bg-primary-50 hover:bg-primary-100 text-primary-700 text-xs font-medium rounded-lg transition-colors self-center flex-shrink-0"
        >
          Quick Fix
        </button>
      )}
    </div>
  );
};

interface DesignAssistantProps {
  onLayoutUpdate?: (layout: Layout) => void;
}

export const DesignAssistant: React.FC<DesignAssistantProps> = ({ onLayoutUpdate }) => {
  const { 
    validationResult, 
    layout: selectedLayout, 
    setLayout: updateLayout, 
    canvasSize, 
    isAlcohol, 
    setValidationResult 
  } = useStore();

  // Auto-fix implementations
  const applyAutoFix = useCallback(
    async (issue: ValidationIssue) => {
      if (!selectedLayout) return;

      let newLayout = { ...selectedLayout, elements: [...selectedLayout.elements] };

      switch (issue.code) {
        case 'TESCO_TAG_MISSING':
          newLayout.elements = [
            ...newLayout.elements,
            {
              type: 'tesco_tag' as const,
              text: 'Available at Tesco',
              x: 65,
              y: 88,
              width: 30,
              height: 8,
            },
          ];
          break;

        case 'TESCO_TAG_INVALID':
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (e.type === 'tesco_tag') {
              return { ...e, text: 'Available at Tesco' };
            }
            return e;
          });
          break;

        case 'FONT_SIZE_TOO_SMALL':
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if ((e.type === 'headline' || e.type === 'subhead') && (e.font_size || 0) < 20) {
              return { ...e, font_size: e.type === 'headline' ? 48 : 24 };
            }
            return e;
          });
          break;

        case 'SAFE_ZONE_TOP_VIOLATION':
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (e.type !== 'background' && (e.y || 0) < 12) {
              return { ...e, y: 15 };
            }
            return e;
          });
          break;

        case 'SAFE_ZONE_BOTTOM_VIOLATION':
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (e.type !== 'background' && e.type !== 'tesco_tag' && (e.y || 0) + (e.height || 0) > 87) {
              return { ...e, y: 70 };
            }
            return e;
          });
          break;

        case 'DRINKAWARE_MISSING':
          newLayout.elements = [
            ...newLayout.elements,
            {
              type: 'drinkaware' as const,
              x: 35,
              y: 94,
              width: 30,
              height: 3,
              color: '#000000',
            },
          ];
          break;

        case 'DRINKAWARE_COLOR_INVALID':
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (e.type === 'drinkaware') {
              return { ...e, color: '#000000' };
            }
            return e;
          });
          break;

        case 'WCAG_CONTRAST_FAIL':
          const bgElement = newLayout.elements.find((e: LayoutElement) => e.type === 'background');
          const bgColor = bgElement?.color || '#FFFFFF';
          const isLightBg = isLightColor(bgColor);
          
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (e.type === 'headline' || e.type === 'subhead') {
              return { ...e, color: isLightBg ? '#1F2937' : '#FFFFFF' };
            }
            return e;
          });
          break;

        default:
          console.log('No auto-fix available for:', issue.code);
          return;
      }

      updateLayout(newLayout);
      onLayoutUpdate?.(newLayout);

      // Re-validate
      try {
        const result = await validateLayout({
          layout: newLayout,
          canvas_size: canvasSize,
          is_alcohol: isAlcohol,
          channel: canvasSize === '1080x1920' ? 'stories' : 'facebook',
        });
        setValidationResult(result);
      } catch (error) {
        console.error('Re-validation failed:', error);
      }
    },
    [selectedLayout, updateLayout, onLayoutUpdate, canvasSize, isAlcohol, setValidationResult]
  );

  // Fix all issues
  const handleFixAll = useCallback(async () => {
    if (!validationResult?.issues) return;
    
    for (const issue of validationResult.issues) {
      await applyAutoFix(issue);
    }
  }, [validationResult, applyAutoFix]);

  const issues = validationResult?.issues || [];
  const hardIssues = issues.filter(i => i.severity === 'hard');
  const softIssues = issues.filter(i => i.severity === 'warn');
  const isExportReady = hardIssues.length === 0;

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="px-4 py-4 bg-white border-b border-gray-100">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-800">Design Assistant</h3>
          {issues.length > 0 && (
            <button
              onClick={handleFixAll}
              className="text-xs text-primary-600 hover:text-primary-800 font-medium"
            >
              Fix All
            </button>
          )}
        </div>
        
        {/* Status Badge */}
        <div className={clsx(
          "flex items-center gap-2 px-3 py-2 rounded-lg",
          isExportReady ? "bg-green-50" : "bg-amber-50"
        )}>
          {isExportReady ? (
            <>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium text-green-700">Ready to export</span>
            </>
          ) : (
            <>
              <div className="w-2 h-2 bg-amber-500 rounded-full" />
              <span className="text-sm font-medium text-amber-700">
                {hardIssues.length} suggestion{hardIssues.length !== 1 ? 's' : ''} before export
              </span>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {issues.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-2xl flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h4 className="text-lg font-medium text-gray-800 mb-1">Looking Good!</h4>
            <p className="text-sm text-gray-500">Your design is ready for export.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Hard issues first */}
            {hardIssues.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                  Required for Export
                </p>
                <div className="space-y-2">
                  {hardIssues.map((issue, index) => (
                    <SuggestionCard
                      key={`hard-${index}`}
                      issue={issue}
                      onFix={() => applyAutoFix(issue)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Soft issues */}
            {softIssues.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                  Recommendations
                </p>
                <div className="space-y-2">
                  {softIssues.map((issue, index) => (
                    <SuggestionCard
                      key={`soft-${index}`}
                      issue={issue}
                      onFix={() => applyAutoFix(issue)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer - Export Info */}
      <div className="px-4 py-3 bg-white border-t border-gray-100">
        <p className="text-xs text-gray-500 text-center">
          {isExportReady 
            ? "✨ Press Ctrl+E to export" 
            : "Fix required items to enable export"
          }
        </p>
      </div>
    </div>
  );
};

export default DesignAssistant;
