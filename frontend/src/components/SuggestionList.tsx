/**
 * Suggestion List Component
 * Displays layout suggestions from LLM or stub generation
 */
import React from 'react';
import clsx from 'clsx';
import { useStore } from '../store';
import { Layout, CANVAS_CONFIGS } from '../types';
import { getAssetUrl } from '../api';

interface SuggestionCardProps {
  layout: Layout;
  isSelected: boolean;
  onClick: () => void;
}

const SuggestionCard: React.FC<SuggestionCardProps> = ({ layout, isSelected, onClick }) => {
  const canvasSize = useStore((state) => state.canvasSize);
  const config = CANVAS_CONFIGS[canvasSize];

  // Generate preview
  const previewScale = 100 / config.height;
  const previewWidth = config.width * previewScale;
  const previewHeight = 100;

  // Get background color
  const bgElement = layout.elements.find((e) => e.type === 'background');
  const bgColor = bgElement?.color || '#FFFFFF';

  return (
    <div
      className={clsx(
        'suggestion-card flex-shrink-0 w-32 cursor-pointer transition-all',
        isSelected && 'selected ring-2 ring-primary-500'
      )}
      onClick={onClick}
    >
      {/* Mini preview */}
      <div
        className="w-full relative overflow-hidden rounded border border-gray-200"
        style={{
          height: previewHeight,
          backgroundColor: bgColor,
        }}
      >
        {/* Render preview elements */}
        {layout.elements
          .filter((e) => e.type !== 'background')
          .map((element, i) => {
            const x = (element.x || 0) * (previewWidth / 100);
            const y = (element.y || 0) * (previewHeight / 100);
            const width = Math.max((element.width || 10) * (previewWidth / 100), 4);
            const height = Math.max((element.height || 10) * (previewHeight / 100), 4);

            // For packshots and logos, try to show actual image
            if ((element.type === 'packshot' || element.type === 'logo') && element.asset) {
              const assetUrl = getAssetUrl(element.asset);
              return (
                <div key={i} className="absolute" style={{ left: x, top: y, width, height }}>
                  <img
                    src={assetUrl}
                    alt={element.type}
                    className="w-full h-full object-contain"
                    onLoad={() => console.log('[SuggestionList] Loaded:', assetUrl)}
                    onError={(e) => {
                      console.error('[SuggestionList] Failed to load:', assetUrl);
                      // Replace failed image with colored placeholder
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                      if (target.nextElementSibling) {
                        (target.nextElementSibling as HTMLElement).style.display = 'block';
                      }
                    }}
                  />
                  <div 
                    className="w-full h-full rounded-sm hidden" 
                    style={{ 
                      backgroundColor: element.type === 'packshot' ? '#8B5CF6' : '#10B981',
                      opacity: 0.8 
                    }} 
                  />
                </div>
              );
            }

            // For other elements, show colored rectangles
            let color = '#ccc';
            if (element.type === 'packshot') color = '#8B5CF6';
            if (element.type === 'headline') color = element.color || '#000';
            if (element.type === 'subhead') color = element.color || '#666';
            if (element.type === 'tesco_tag') color = '#00539F';
            if (element.type === 'value_tile') color = '#FFD100';
            if (element.type === 'logo') color = '#10B981';

            return (
              <div
                key={i}
                className="absolute rounded-sm"
                style={{
                  left: x,
                  top: y,
                  width,
                  height,
                  backgroundColor: color,
                  opacity: 0.8,
                }}
              />
            );
          })}
      </div>

      {/* Layout info */}
      <div className="mt-2 text-xs">
        <div className="font-medium text-gray-800 truncate">{layout.id}</div>
        <div className="text-gray-500">Score: {(layout.score * 100).toFixed(0)}%</div>
      </div>
    </div>
  );
};

interface SuggestionListProps {
  onLayoutSelect?: (layout: Layout) => void;
}

export const SuggestionList: React.FC<SuggestionListProps> = ({ onLayoutSelect }) => {
  const { suggestions, layout: selectedLayout, selectSuggestion } = useStore();

  const handleSelect = (suggestion: Layout) => {
    // Find the suggestion by matching the layout
    const found = suggestions.find(s => s.layout.id === suggestion.id);
    if (found) {
      selectSuggestion(found.id);
    }
    onLayoutSelect?.(suggestion);
  };

  // Get layouts from suggestions
  const layouts = suggestions.map(s => s.layout);

  if (layouts.length === 0) {
    return (
      <div className="panel h-full">
        <div className="panel-header">Layout Suggestions</div>
        <div className="panel-body text-center text-gray-500">
          <p>No layouts generated yet.</p>
          <p className="text-sm mt-1">Upload assets and generate layouts to see suggestions.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header flex justify-between items-center">
        <span>Layout Suggestions ({layouts.length})</span>
        <button
          className="text-sm text-primary-600 hover:text-primary-800"
          onClick={() => {
            // This would regenerate layouts
            document.getElementById('generate-btn')?.click();
          }}
        >
          Regenerate
        </button>
      </div>
      <div className="panel-body flex-1 overflow-x-auto">
        <div className="flex gap-3 pb-2">
          {layouts.map((layout) => (
            <SuggestionCard
              key={layout.id}
              layout={layout}
              isSelected={selectedLayout?.id === layout.id}
              onClick={() => handleSelect(layout)}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default SuggestionList;
