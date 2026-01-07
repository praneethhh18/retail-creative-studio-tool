/**
 * Layout Gallery Component
 * Animated layout suggestions with smooth transitions
 */
import React, { useState } from 'react';
import clsx from 'clsx';
import { useStore } from '../store';
import { Layout, CANVAS_CONFIGS } from '../types';
import { getAssetUrl } from '../api';

interface LayoutPreviewProps {
  layout: Layout;
  isSelected: boolean;
  onClick: () => void;
  onApply: () => void;
}

const LayoutPreview: React.FC<LayoutPreviewProps> = ({ layout, isSelected, onClick, onApply }) => {
  const canvasSize = useStore((state) => state.canvasSize);
  const config = CANVAS_CONFIGS[canvasSize];
  const [isHovered, setIsHovered] = useState(false);

  const previewHeight = 120;
  const previewWidth = (config.width / config.height) * previewHeight;

  const bgElement = layout.elements.find((e) => e.type === 'background');
  const bgColor = bgElement?.color || '#FFFFFF';

  return (
    <div
      className={clsx(
        'relative group flex-shrink-0 cursor-pointer transition-all duration-300 rounded-xl overflow-hidden',
        isSelected 
          ? 'ring-2 ring-primary-500 ring-offset-2 scale-105 shadow-xl' 
          : 'hover:scale-102 hover:shadow-lg'
      )}
      style={{ width: previewWidth }}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Preview Canvas */}
      <div
        className="relative overflow-hidden transition-transform duration-300"
        style={{
          height: previewHeight,
          backgroundColor: bgColor,
        }}
      >
        {/* Animated elements */}
        {layout.elements
          .filter((e) => e.type !== 'background')
          .map((element, i) => {
            const x = ((element.x || 0) / 100) * previewWidth;
            const y = ((element.y || 0) / 100) * previewHeight;
            const width = Math.max(((element.width || 10) / 100) * previewWidth, 4);
            const height = Math.max(((element.height || 10) / 100) * previewHeight, 4);

            // Images
            if ((element.type === 'packshot' || element.type === 'logo') && element.asset) {
              return (
                <div
                  key={i}
                  className="absolute transition-all duration-500 ease-out"
                  style={{
                    left: x,
                    top: y,
                    width,
                    height,
                    transform: isHovered ? 'scale(1.05)' : 'scale(1)',
                  }}
                >
                  <img
                    src={getAssetUrl(element.asset)}
                    alt={element.type}
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                </div>
              );
            }

            // Colored placeholders
            let color = '#E5E7EB';
            if (element.type === 'packshot') color = '#A78BFA';
            if (element.type === 'headline') color = element.color || '#1F2937';
            if (element.type === 'subhead') color = element.color || '#6B7280';
            if (element.type === 'tesco_tag') color = '#00539F';
            if (element.type === 'value_tile') color = '#FFD100';
            if (element.type === 'logo') color = '#10B981';

            return (
              <div
                key={i}
                className="absolute rounded-sm transition-all duration-300"
                style={{
                  left: x,
                  top: y,
                  width,
                  height,
                  backgroundColor: color,
                  opacity: element.type === 'headline' || element.type === 'subhead' ? 1 : 0.9,
                }}
              />
            );
          })}

        {/* Hover overlay */}
        <div className={clsx(
          'absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent transition-opacity duration-300',
          isHovered ? 'opacity-100' : 'opacity-0'
        )}>
          <div className="absolute bottom-2 left-2 right-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onApply();
              }}
              className="w-full py-1.5 bg-white text-gray-900 text-xs font-medium rounded-lg hover:bg-gray-100 transition-colors"
            >
              Apply Layout
            </button>
          </div>
        </div>
      </div>

      {/* Score indicator */}
      <div className="absolute top-2 right-2 px-2 py-0.5 bg-white/90 backdrop-blur-sm rounded-full text-xs font-medium text-gray-700">
        {(layout.score * 100).toFixed(0)}%
      </div>
    </div>
  );
};

interface LayoutGalleryProps {
  onLayoutSelect?: (layout: Layout) => void;
}

export const LayoutGallery: React.FC<LayoutGalleryProps> = ({ onLayoutSelect }) => {
  const { suggestions, layout: selectedLayout, setLayout } = useStore();
  const [isAnimating, setIsAnimating] = useState(false);

  const layouts = suggestions.map(s => s.layout);

  const handleApplyLayout = (layout: Layout) => {
    setIsAnimating(true);
    
    // Animate transition
    setTimeout(() => {
      setLayout(layout);
      onLayoutSelect?.(layout);
      setIsAnimating(false);
    }, 300);
  };

  if (layouts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-white border-t border-gray-100">
        <div className="text-center py-6">
          <div className="w-12 h-12 mx-auto mb-3 bg-gray-100 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
            </svg>
          </div>
          <p className="text-gray-500 text-sm">No layouts yet</p>
          <p className="text-gray-400 text-xs mt-1">Upload assets and click Generate</p>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx(
      'h-full bg-white border-t border-gray-100 transition-opacity duration-300',
      isAnimating && 'opacity-50'
    )}>
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-800">Layout Ideas</h3>
          <span className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs font-medium rounded-full">
            {layouts.length}
          </span>
        </div>
        <button
          onClick={() => document.getElementById('generate-btn')?.click()}
          className="text-xs text-primary-600 hover:text-primary-800 font-medium flex items-center gap-1 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Regenerate
        </button>
      </div>

      <div className="px-4 pb-4 overflow-x-auto">
        <div className="flex gap-4">
          {layouts.map((layout) => (
            <LayoutPreview
              key={layout.id}
              layout={layout}
              isSelected={selectedLayout?.id === layout.id}
              onClick={() => handleApplyLayout(layout)}
              onApply={() => handleApplyLayout(layout)}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default LayoutGallery;
