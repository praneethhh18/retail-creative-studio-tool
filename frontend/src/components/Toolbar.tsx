/**
 * Toolbar Component
 * Top navigation with undo/redo, channel selection, and actions
 */
import React from 'react';
import clsx from 'clsx';
import { useStore } from '../store';

const CHANNELS = [
  { id: 'facebook_feed', label: 'Facebook Feed', width: 1200, height: 628 },
  { id: 'instagram_feed', label: 'Instagram Feed', width: 1080, height: 1080 },
  { id: 'instagram_story', label: 'Instagram Story', width: 1080, height: 1920 },
  { id: 'instore_a4', label: 'In-Store A4', width: 2480, height: 3508 },
];

interface ToolbarProps {
  onExport: () => void;
  onGenerate: () => void;
  onValidate: () => void;
  onWizard?: () => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({ onExport, onGenerate, onValidate, onWizard }) => {
  const {
    canUndo,
    canRedo,
    undo,
    redo,
    selectedChannel,
    setSelectedChannel,
    isLoading,
    validationResult,
  } = useStore();

  const hasErrors = validationResult?.issues.some((i) => i.severity === 'hard');
  const hasWarnings = validationResult?.issues.some((i) => i.severity === 'warn');

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-2">
      <div className="flex items-center justify-between">
        {/* Left: Logo and Title */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="font-semibold text-gray-900">Retail Creative Tool</span>
          </div>

          {/* Undo/Redo */}
          <div className="flex items-center gap-1 border-l border-gray-200 pl-4">
            <button
              onClick={undo}
              disabled={!canUndo()}
              className={clsx(
                'p-2 rounded-lg transition-colors',
                canUndo()
                  ? 'text-gray-700 hover:bg-gray-100'
                  : 'text-gray-300 cursor-not-allowed'
              )}
              title="Undo (Ctrl+Z)"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
              </svg>
            </button>
            <button
              onClick={redo}
              disabled={!canRedo()}
              className={clsx(
                'p-2 rounded-lg transition-colors',
                canRedo()
                  ? 'text-gray-700 hover:bg-gray-100'
                  : 'text-gray-300 cursor-not-allowed'
              )}
              title="Redo (Ctrl+Y)"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10H11a8 8 0 00-8 8v2m18-10l-6 6m6-6l-6-6" />
              </svg>
            </button>
          </div>
        </div>

        {/* Center: Channel Selection */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Channel:</label>
          <select
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {CHANNELS.map((channel) => (
              <option key={channel.id} value={channel.id}>
                {channel.label} ({channel.width}×{channel.height})
              </option>
            ))}
          </select>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Design Wizard */}
          {onWizard && (
            <button
              onClick={onWizard}
              disabled={isLoading}
              className={clsx(
                'btn flex items-center gap-2 px-3 py-1.5 text-sm',
                'bg-gradient-to-r from-indigo-500 to-purple-500 text-white hover:from-indigo-600 hover:to-purple-600',
                isLoading && 'opacity-50 cursor-not-allowed'
              )}
              title="Open guided design wizard for easy creative creation"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
              Wizard
            </button>
          )}

          {/* Generate Suggestions */}
          <button
            onClick={onGenerate}
            disabled={isLoading}
            className={clsx(
              'btn flex items-center gap-2 px-3 py-1.5 text-sm',
              'bg-purple-100 text-purple-700 hover:bg-purple-200',
              isLoading && 'opacity-50 cursor-not-allowed'
            )}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Generate
          </button>

          {/* Validate */}
          <button
            onClick={onValidate}
            disabled={isLoading}
            className={clsx(
              'btn flex items-center gap-2 px-3 py-1.5 text-sm relative',
              hasErrors
                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                : hasWarnings
                  ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
              isLoading && 'opacity-50 cursor-not-allowed'
            )}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Validate
            {validationResult && validationResult.issues.length > 0 && (
              <span className={clsx(
                'absolute -top-1 -right-1 w-4 h-4 text-xs font-bold rounded-full flex items-center justify-center',
                hasErrors ? 'bg-red-500 text-white' : 'bg-yellow-500 text-white'
              )}>
                {validationResult.issues.length}
              </span>
            )}
          </button>

          {/* Export */}
          <button
            onClick={onExport}
            disabled={isLoading || hasErrors}
            className={clsx(
              'btn-primary flex items-center gap-2 px-4 py-1.5 text-sm',
              (isLoading || hasErrors) && 'opacity-50 cursor-not-allowed'
            )}
            title={hasErrors ? 'Fix validation errors before exporting' : 'Export creative'}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Export
          </button>
        </div>
      </div>
    </header>
  );
};

export default Toolbar;
