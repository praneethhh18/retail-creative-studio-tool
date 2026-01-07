/**
 * Main Application Component
 * Retail Media Creative Tool - Creative-first AI-powered design
 */
import React, { useState, useCallback, useEffect } from 'react';
import { useStore } from './store';
import {
  AssetLibrary,
  CreativeCanvas,
  ExportDialog,
  LayoutGallery,
  Toolbar,
  DesignAssistant,
} from './components';
import { DesignWizard } from './components/DesignWizard';
import { generateLayouts, validateLayout as validateLayoutAPI } from './api';
import { Layout, LayoutSuggestion } from './types';

const App: React.FC = () => {
  const {
    layout,
    setLayout,
    assets,
    selectedChannel,
    setValidationResult,
    setSuggestions,
    setIsLoading,
    isLoading,
  } = useStore();

  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  // Generate layout suggestions
  const handleGenerate = useCallback(async () => {
    if (assets.length === 0) {
      alert('Please upload at least one asset first');
      return;
    }

    setIsGenerating(true);
    setIsLoading(true);

    try {
      // Prepare asset context for LLM
      const packshots = assets.filter((a) => a.type === 'packshot');
      const logos = assets.filter((a) => a.type === 'logo');
      const backgrounds = assets.filter((a) => a.type === 'background');

      // Get palette from first packshot
      const palette = packshots[0]?.palette || ['#ffffff', '#000000'];

      // Use cleaned paths (full filenames) for layout generation
      const result = await generateLayouts({
        packshot_ids: packshots.map((a) => a.cleanedPath || a.originalPath),
        logo_ids: logos.map((a) => a.cleanedPath || a.originalPath),
        background_id: backgrounds[0]?.cleanedPath || backgrounds[0]?.originalPath,
        palette,
        channel: selectedChannel,
        user_prompt: 'Create a professional retail creative with the uploaded products'
      });

      // Convert API response to suggestions (API returns 'layouts', not 'suggestions')
      const layoutsArray = result.layouts || result.suggestions || [];
      const suggestions: LayoutSuggestion[] = layoutsArray.map((s, index) => ({
        id: `suggestion-${index}`,
        layout: s as Layout,
        score: 0.9 - index * 0.1,
        reasoning: `AI-generated layout option ${index + 1}`,
      }));

      setSuggestions(suggestions);

      // Auto-select first suggestion if no layout
      if (!layout && suggestions.length > 0) {
        setLayout(suggestions[0].layout);
      }
    } catch (error) {
      console.error('Generate failed:', error);
      const errorMessage = error instanceof Error 
        ? error.message 
        : (typeof error === 'object' && error !== null 
            ? JSON.stringify(error) 
            : String(error));
      alert('Failed to generate layouts: ' + errorMessage);
    } finally {
      setIsGenerating(false);
      setIsLoading(false);
    }
  }, [assets, selectedChannel, layout, setLayout, setSuggestions, setIsLoading]);

  // Validate current layout
  const handleValidate = useCallback(async () => {
    if (!layout) {
      alert('Please create or select a layout first');
      return;
    }

    setIsValidating(true);
    setIsLoading(true);

    try {
      const result = await validateLayoutAPI({ layout, channel: selectedChannel });
      setValidationResult(result);
    } catch (error) {
      console.error('Validation failed:', error);
      alert('Validation failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setIsValidating(false);
      setIsLoading(false);
    }
  }, [layout, selectedChannel, setValidationResult, setIsLoading]);

  // Auto-validate on layout changes
  useEffect(() => {
    if (layout) {
      const timeout = setTimeout(() => {
        handleValidate();
      }, 500);
      return () => clearTimeout(timeout);
    }
  }, [layout]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'e':
            if (!isLoading) {
              e.preventDefault();
              setShowExportDialog(true);
            }
            break;
          case 'g':
            if (!isLoading) {
              e.preventDefault();
              handleGenerate();
            }
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isLoading, handleGenerate]);

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Top Toolbar */}
      <Toolbar
        onExport={() => setShowExportDialog(true)}
        onGenerate={handleGenerate}
        onValidate={handleValidate}
        onWizard={() => setShowWizard(true)}
      />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Asset Library */}
        <aside className="w-64 flex-shrink-0 bg-white shadow-sm overflow-hidden z-10">
          <AssetLibrary />
        </aside>

        {/* Center: Creative Canvas */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <CreativeCanvas />
          </div>

          {/* Bottom: Layout Gallery */}
          <div className="h-44 flex-shrink-0">
            <LayoutGallery />
          </div>
        </main>

        {/* Right Panel: Design Assistant */}
        <aside className="w-80 flex-shrink-0 bg-white shadow-sm overflow-hidden z-10">
          <DesignAssistant />
        </aside>
      </div>

      {/* Loading Overlay - More subtle */}
      {isLoading && (
        <div className="fixed inset-0 bg-white/60 backdrop-blur-sm flex items-center justify-center z-40">
          <div className="bg-white rounded-2xl p-8 shadow-2xl flex flex-col items-center gap-4 animate-scale-in">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary-400 to-purple-500 flex items-center justify-center">
              <svg className="animate-spin w-8 h-8 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <div className="text-center">
              <p className="text-gray-800 font-semibold">
                {isGenerating ? 'Creating Magic ✨' : isValidating ? 'Checking Design' : 'Working...'}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {isGenerating ? 'Generating layout ideas for you' : 'This won\'t take long'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Export Dialog */}
      <ExportDialog
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
      />

      {/* Design Wizard for non-designers */}
      <DesignWizard
        isOpen={showWizard}
        onClose={() => setShowWizard(false)}
        onComplete={(wizardLayout) => {
          setLayout(wizardLayout);
          setShowWizard(false);
          handleValidate();
        }}
      />
    </div>
  );
};

export default App;
