/**
 * Validator Panel Component
 * Displays validation results with issues and auto-fix options
 */
import React, { useCallback } from 'react';
import clsx from 'clsx';
import { useStore } from '../store';
import { ValidationIssue, Layout, LayoutElement } from '../types';
import { validateLayout } from '../api';

interface IssueCardProps {
  issue: ValidationIssue;
  onAutoFix?: () => void;
}

const IssueCard: React.FC<IssueCardProps> = ({ issue, onAutoFix }) => {
  const isHard = issue.severity === 'hard';

  return (
    <div
      className={clsx(
        'p-3 rounded-lg border-l-4 mb-2',
        isHard ? 'bg-red-50 border-red-500' : 'bg-yellow-50 border-yellow-500'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span
              className={clsx(
                'issue-badge',
                isHard ? 'hard' : 'warn'
              )}
            >
              {isHard ? 'Error' : 'Warning'}
            </span>
            <span className="text-xs font-mono text-gray-500">{issue.code}</span>
          </div>
          <p className={clsx('mt-1 text-sm', isHard ? 'text-red-800' : 'text-yellow-800')}>
            {issue.message}
          </p>
          {issue.fix_suggestion && (
            <p className="mt-1 text-xs text-gray-600">
              💡 {issue.fix_suggestion}
            </p>
          )}
        </div>
        {issue.fix_suggestion && onAutoFix && (
          <button
            onClick={onAutoFix}
            className="ml-2 text-xs btn btn-secondary py-1 px-2"
          >
            Auto-fix
          </button>
        )}
      </div>
    </div>
  );
};

interface ValidatorPanelProps {
  onLayoutUpdate?: (layout: Layout) => void;
}

export const ValidatorPanel: React.FC<ValidatorPanelProps> = ({ onLayoutUpdate }) => {
  const { validationResult, layout: selectedLayout, setLayout: updateLayout, canvasSize, isAlcohol, setValidationResult } = useStore();

  // Auto-fix implementations
  const applyAutoFix = useCallback(
    async (issue: ValidationIssue) => {
      if (!selectedLayout) return;

      let newLayout = { ...selectedLayout, elements: [...selectedLayout.elements] };

      switch (issue.code) {
        case 'TESCO_TAG_INVALID':
          // Fix invalid Tesco tag text
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (e.type === 'tesco_tag') {
              return { ...e, text: 'Available at Tesco' };
            }
            return e;
          });
          break;

        case 'FONT_SIZE_TOO_SMALL':
          // Increase font size to minimum
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if ((e.type === 'headline' || e.type === 'subhead') && (e.font_size || 0) < 20) {
              return { ...e, font_size: 20 };
            }
            return e;
          });
          break;

        case 'SAFE_ZONE_TOP_VIOLATION':
        case 'SAFE_ZONE_BOTTOM_VIOLATION':
          // Move element out of safe zone
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (issue.element_id && e.type === issue.element_id.split('-')[0]) {
              if (issue.code === 'SAFE_ZONE_TOP_VIOLATION') {
                return { ...e, y: 12 }; // Move to 12% from top (about 230px for 1920 height)
              } else {
                return { ...e, y: 70 }; // Move to 70% from top
              }
            }
            return e;
          });
          break;

        case 'DRINKAWARE_MISSING':
          // Add drinkaware element
          newLayout.elements = [
            ...newLayout.elements,
            {
              type: 'drinkaware' as const,
              x: 35,
              y: 92,
              width: 30,
              height: 3,
              color: '#000000',
            },
          ];
          break;

        case 'DRINKAWARE_COLOR_INVALID':
          // Fix drinkaware color to black
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (e.type === 'drinkaware') {
              return { ...e, color: '#000000' };
            }
            return e;
          });
          break;

        case 'WCAG_CONTRAST_FAIL':
          // Fix text color for better contrast
          const bgElement = newLayout.elements.find((e: LayoutElement) => e.type === 'background');
          const bgColor = bgElement?.color || '#FFFFFF';
          const isLightBg = isLightColor(bgColor);
          
          newLayout.elements = newLayout.elements.map((e: LayoutElement) => {
            if (e.type === 'headline' || e.type === 'subhead') {
              return { ...e, color: isLightBg ? '#000000' : '#FFFFFF' };
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
        console.error('Validation failed:', error);
      }
    },
    [selectedLayout, updateLayout, onLayoutUpdate, canvasSize, isAlcohol, setValidationResult]
  );

  // Helper to check if color is light
  const isLightColor = (hex: string): boolean => {
    const c = hex.replace('#', '');
    const r = parseInt(c.substring(0, 2), 16);
    const g = parseInt(c.substring(2, 4), 16);
    const b = parseInt(c.substring(4, 6), 16);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness > 128;
  };

  // Fix all auto-fixable issues
  const fixAll = useCallback(async () => {
    if (!validationResult) return;
    
    for (const issue of validationResult.issues) {
      if (issue.fix_suggestion) {
        await applyAutoFix(issue);
      }
    }
  }, [validationResult, applyAutoFix]);

  if (!validationResult) {
    return (
      <div className="panel h-full">
        <div className="panel-header">Validation</div>
        <div className="panel-body text-center text-gray-500">
          <p>Select a layout to see validation results.</p>
        </div>
      </div>
    );
  }

  const hardIssues = validationResult.issues.filter((i) => i.severity === 'hard');
  const warnIssues = validationResult.issues.filter((i) => i.severity === 'warn');
  const hasAutoFixable = validationResult.issues.some((i) => i.fix_suggestion);

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span>Validation</span>
          {validationResult.ok ? (
            <span className="text-xs px-2 py-0.5 bg-green-100 text-green-800 rounded-full">
              ✓ Passed
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 bg-red-100 text-red-800 rounded-full">
              ✗ {hardIssues.length} error{hardIssues.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {hasAutoFixable && (
          <button onClick={fixAll} className="text-xs btn btn-primary py-1 px-2">
            Fix All
          </button>
        )}
      </div>

      <div className="panel-body flex-1 overflow-y-auto">
        {validationResult.ok && validationResult.issues.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-4xl mb-2">✅</div>
            <p className="text-green-700 font-medium">All checks passed!</p>
            <p className="text-sm text-gray-500 mt-1">
              {validationResult.checked_rules.length} rules verified
            </p>
          </div>
        ) : (
          <div>
            {/* Hard failures (errors) */}
            {hardIssues.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-red-800 mb-2">
                  Errors ({hardIssues.length})
                </h4>
                {hardIssues.map((issue, i) => (
                  <IssueCard
                    key={`hard-${i}`}
                    issue={issue}
                    onAutoFix={issue.fix_suggestion ? () => applyAutoFix(issue) : undefined}
                  />
                ))}
              </div>
            )}

            {/* Warnings */}
            {warnIssues.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-yellow-800 mb-2">
                  Warnings ({warnIssues.length})
                </h4>
                {warnIssues.map((issue, i) => (
                  <IssueCard
                    key={`warn-${i}`}
                    issue={issue}
                    onAutoFix={issue.fix_suggestion ? () => applyAutoFix(issue) : undefined}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Checked rules summary */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <details className="text-xs text-gray-500">
            <summary className="cursor-pointer hover:text-gray-700">
              {validationResult.checked_rules.length} rules checked
            </summary>
            <ul className="mt-2 ml-4 list-disc">
              {validationResult.checked_rules.map((rule, i) => (
                <li key={i}>{rule}</li>
              ))}
            </ul>
          </details>
        </div>
      </div>
    </div>
  );
};

export default ValidatorPanel;
