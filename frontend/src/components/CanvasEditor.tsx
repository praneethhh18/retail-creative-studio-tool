/**
 * Canvas Editor Component
 * Interactive Konva canvas for editing layouts
 */
import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Stage, Layer, Rect, Text, Image as KonvaImage, Transformer, Group } from 'react-konva';
import { useStore } from '../store';
import { Layout, LayoutElement, CANVAS_CONFIGS } from '../types';
import { getAssetUrl, validateLayout } from '../api';

// Constants for locked elements
const LOCKED_TYPES = ['value_tile', 'tesco_tag', 'drinkaware'];

// Helper to convert percentage to pixels
const pctToPx = (pct: number, total: number): number => (pct / 100) * total;

// Asset image component
interface AssetImageProps {
  src: string;
  x: number;
  y: number;
  width: number;
  height: number;
  draggable: boolean;
  onDragEnd?: (e: { target: { x: () => number; y: () => number } }) => void;
  onTransformEnd?: (e: { target: { x: () => number; y: () => number; width: () => number; height: () => number; scaleX: () => number; scaleY: () => number } }) => void;
  isSelected?: boolean;
  onSelect?: () => void;
}

const AssetImage: React.FC<AssetImageProps> = ({
  src,
  x,
  y,
  width,
  height,
  draggable,
  onDragEnd,
  isSelected,
  onSelect,
}) => {
  const assetUrl = getAssetUrl(src);
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [status, setStatus] = useState<'loading' | 'loaded' | 'failed'>('loading');
  
  const shapeRef = useRef<Konva.Image>(null);
  const trRef = useRef<Konva.Transformer>(null);

  // Custom image loading - more reliable than useImage hook
  useEffect(() => {
    if (!assetUrl) {
      setStatus('failed');
      return;
    }

    const img = new window.Image();
    img.crossOrigin = 'anonymous';
    
    img.onload = () => {
      console.log('[AssetImage] Image loaded successfully:', assetUrl);
      setImage(img);
      setStatus('loaded');
    };
    
    img.onerror = (e) => {
      console.error('[AssetImage] Image failed to load:', assetUrl, e);
      setStatus('failed');
    };
    
    console.log('[AssetImage] Starting to load:', assetUrl);
    img.src = assetUrl;
    
    return () => {
      img.onload = null;
      img.onerror = null;
    };
  }, [assetUrl]);

  useEffect(() => {
    if (isSelected && trRef.current && shapeRef.current) {
      trRef.current.nodes([shapeRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, [isSelected]);
  
  // Show loading placeholder if image is loading
  if (status === 'loading') {
    return (
      <Group>
        <Rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill="#e5e7eb"
          stroke="#9ca3af"
          strokeWidth={1}
          dash={[5, 5]}
        />
        <Text
          x={x + width / 2 - 40}
          y={y + height / 2 - 8}
          text="Loading..."
          fontSize={14}
          fill="#6b7280"
        />
      </Group>
    );
  }
  
  // Show error placeholder if image failed to load
  if (status === 'failed' || !image) {
    return (
      <Group>
        <Rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill="#fef2f2"
          stroke="#ef4444"
          strokeWidth={2}
        />
        <Text
          x={x + 5}
          y={y + height / 2 - 8}
          text={`⚠️ ${src ? 'Image failed' : 'No image'}`}
          fontSize={12}
          fill="#ef4444"
          width={width - 10}
        />
      </Group>
    );
  }

  return (
    <>
      <KonvaImage
        ref={shapeRef}
        image={image}
        x={x}
        y={y}
        width={width}
        height={height}
        draggable={draggable}
        onClick={onSelect}
        onTap={onSelect}
        onDragEnd={onDragEnd}
      />
      {isSelected && (
        <Transformer
          ref={trRef}
          boundBoxFunc={(oldBox, newBox) => {
            // Limit resize
            if (newBox.width < 20 || newBox.height < 20) {
              return oldBox;
            }
            return newBox;
          }}
        />
      )}
    </>
  );
};

// Import Konva types
import Konva from 'konva';

interface CanvasEditorProps {
  onLayoutChange?: (layout: Layout) => void;
}

export const CanvasEditor: React.FC<CanvasEditorProps> = ({ onLayoutChange }) => {
  const { layout: selectedLayout, setLayout, canvasSize, isAlcohol, setValidationResult } = useStore();
  const updateLayout = (updated: Layout) => setLayout(updated);
  const stageRef = useRef<Konva.Stage>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [editingText, setEditingText] = useState<{ index: number; text: string } | null>(null);

  const config = CANVAS_CONFIGS[canvasSize];
  
  // Calculate scale to fit canvas in container
  useEffect(() => {
    const updateScale = () => {
      const container = document.getElementById('canvas-container');
      if (container) {
        const containerWidth = container.clientWidth - 40;
        const containerHeight = container.clientHeight - 40;
        const scaleX = containerWidth / config.width;
        const scaleY = containerHeight / config.height;
        setScale(Math.min(scaleX, scaleY, 1));
      }
    };

    updateScale();
    window.addEventListener('resize', updateScale);
    return () => window.removeEventListener('resize', updateScale);
  }, [config.width, config.height]);

  // Validate layout on changes
  const runValidation = useCallback(async (layout: Layout) => {
    try {
      const result = await validateLayout({
        layout,
        canvas_size: canvasSize,
        is_alcohol: isAlcohol,
        channel: canvasSize === '1080x1920' ? 'stories' : 'facebook',
      });
      setValidationResult(result);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  }, [canvasSize, isAlcohol, setValidationResult]);

  // Update element position
  const handleDragEnd = useCallback(
    (elementIndex: number, e: { target: { x: () => number; y: () => number } }) => {
      if (!selectedLayout) return;

      const x = (e.target.x() / config.width) * 100;
      const y = (e.target.y() / config.height) * 100;

      const newElements = [...selectedLayout.elements];
      newElements[elementIndex] = {
        ...newElements[elementIndex],
        x: Math.max(0, Math.min(100 - (newElements[elementIndex].width || 0), x)),
        y: Math.max(0, Math.min(100 - (newElements[elementIndex].height || 0), y)),
      };

      const newLayout = { ...selectedLayout, elements: newElements };
      updateLayout(newLayout);
      onLayoutChange?.(newLayout);
      runValidation(newLayout);
    },
    [selectedLayout, config.width, config.height, updateLayout, onLayoutChange, runValidation]
  );

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'z') {
          e.preventDefault();
          useStore.getState().undo();
        } else if (e.key === 'y') {
          e.preventDefault();
          useStore.getState().redo();
        } else if (e.key === 'e') {
          e.preventDefault();
          // Trigger export
          document.getElementById('export-btn')?.click();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Deselect when clicking on empty area
  const checkDeselect = (e: Konva.KonvaEventObject<MouseEvent | TouchEvent>) => {
    const clickedOnEmpty = e.target === e.target.getStage();
    if (clickedOnEmpty) {
      setSelectedId(null);
      setEditingText(null);
    }
  };

  // Handle text editing
  const handleTextEdit = (elementIndex: number, currentText: string) => {
    setEditingText({ index: elementIndex, text: currentText });
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (editingText) {
      setEditingText({ ...editingText, text: e.target.value });
    }
  };

  const handleTextSave = () => {
    if (!editingText || !selectedLayout) return;
    
    const newElements = [...selectedLayout.elements];
    newElements[editingText.index] = {
      ...newElements[editingText.index],
      text: editingText.text,
    };
    
    const newLayout = { ...selectedLayout, elements: newElements };
    updateLayout(newLayout);
    setEditingText(null);
  };

  if (!selectedLayout) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-100 rounded-lg relative">
        <div className="text-center text-gray-500 p-8">
          <svg
            className="mx-auto h-16 w-16 text-gray-400 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <h3 className="text-lg font-semibold text-gray-700 mb-2">Welcome to Retail Creative Tool</h3>
          <p className="text-sm mb-4">Get started by:</p>
          <ol className="text-left text-sm space-y-2 mb-6">
            <li className="flex items-center gap-2">
              <span className="w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-xs">1</span>
              Upload product images in the Asset Library (left panel)
            </li>
            <li className="flex items-center gap-2">
              <span className="w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-xs">2</span>
              Click "Generate" to create AI layouts, or use "Wizard" for guided mode
            </li>
            <li className="flex items-center gap-2">
              <span className="w-6 h-6 bg-primary-600 text-white rounded-full flex items-center justify-center text-xs">3</span>
              Drag elements to customize, double-click text to edit
            </li>
          </ol>
        </div>
      </div>
    );
  }

  // Get background color
  const bgElement = selectedLayout.elements.find((e: LayoutElement) => e.type === 'background');
  const bgColor = bgElement?.color || '#FFFFFF';

  // Handle background color change
  const handleBgColorChange = (color: string) => {
    const newElements = selectedLayout.elements.map((el) => 
      el.type === 'background' ? { ...el, color } : el
    );
    updateLayout({ ...selectedLayout, elements: newElements });
  };

  return (
    <div id="canvas-container" className="w-full h-full flex items-center justify-center bg-gray-200 p-4 relative">
      {/* Canvas Controls */}
      <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg p-3 z-10">
        <div className="flex items-center gap-3">
          <label className="text-xs text-gray-600">Background:</label>
          <input
            type="color"
            value={bgColor}
            onChange={(e) => handleBgColorChange(e.target.value)}
            className="w-8 h-8 rounded cursor-pointer border border-gray-300"
            title="Change background color"
          />
          <div className="flex gap-1">
            {['#FFFFFF', '#F3F4F6', '#1F2937', '#DC2626', '#059669', '#2563EB'].map((color) => (
              <button
                key={color}
                onClick={() => handleBgColorChange(color)}
                className="w-6 h-6 rounded border border-gray-200 hover:scale-110 transition-transform"
                style={{ backgroundColor: color }}
                title={`Set background to ${color}`}
              />
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-200">
          <span className="text-xs text-gray-600">Add:</span>
          <button
            onClick={() => {
              const newElement: LayoutElement = {
                type: 'headline',
                text: 'New Headline',
                x: 10,
                y: 20,
                width: 80,
                height: 12,
                font_size: 48,
                color: '#1F2937',
              };
              const newElements = [...selectedLayout.elements, newElement];
              updateLayout({ ...selectedLayout, elements: newElements });
            }}
            className="px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-xs font-medium"
            title="Add headline text"
          >
            + Text
          </button>
          <button
            onClick={() => {
              const newElement: LayoutElement = {
                type: 'value_tile',
                x: 5,
                y: 5,
                width: 20,
                height: 15,
                text: '£XX.XX',
              };
              const newElements = [...selectedLayout.elements, newElement];
              updateLayout({ ...selectedLayout, elements: newElements });
            }}
            className="px-2 py-1 bg-yellow-100 hover:bg-yellow-200 rounded text-xs font-medium"
            title="Add value tile"
          >
            + Price
          </button>
        </div>
      </div>

      <div
        style={{
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
          backgroundColor: '#fff',
        }}
      >
        <Stage
          ref={stageRef}
          width={config.width * scale}
          height={config.height * scale}
          scaleX={scale}
          scaleY={scale}
          onMouseDown={checkDeselect}
          onTouchStart={checkDeselect}
        >
          <Layer>
            {/* Background */}
            <Rect x={0} y={0} width={config.width} height={config.height} fill={bgColor} />

            {/* Safe zones indicator for Stories */}
            {canvasSize === '1080x1920' && (
              <>
                <Rect
                  x={0}
                  y={0}
                  width={config.width}
                  height={200}
                  fill="rgba(255, 0, 0, 0.1)"
                  stroke="rgba(255, 0, 0, 0.3)"
                  strokeWidth={1}
                  dash={[5, 5]}
                />
                <Rect
                  x={0}
                  y={config.height - 250}
                  width={config.width}
                  height={250}
                  fill="rgba(255, 0, 0, 0.1)"
                  stroke="rgba(255, 0, 0, 0.3)"
                  strokeWidth={1}
                  dash={[5, 5]}
                />
              </>
            )}

            {/* Render elements */}
            {selectedLayout.elements
              .filter((e: LayoutElement) => e.type !== 'background')
              .sort((a: LayoutElement, b: LayoutElement) => (a.z || 0) - (b.z || 0))
              .map((element: LayoutElement, index: number) => {
                const elementId = `${element.type}-${index}`;
                const isLocked = LOCKED_TYPES.includes(element.type);
                const isDraggable = !isLocked;

                const x = pctToPx(element.x || 0, config.width);
                const y = pctToPx(element.y || 0, config.height);
                const width = pctToPx(element.width || 20, config.width);
                const height = pctToPx(element.height || 10, config.height);

                if (element.type === 'packshot' || element.type === 'logo') {
                  return (
                    <AssetImage
                      key={elementId}
                      src={element.asset || ''}
                      x={x}
                      y={y}
                      width={width}
                      height={height}
                      draggable={isDraggable}
                      onDragEnd={(e) => handleDragEnd(index + 1, e)}
                      isSelected={selectedId === elementId}
                      onSelect={() => setSelectedId(elementId)}
                    />
                  );
                }

                if (element.type === 'headline' || element.type === 'subhead') {
                  const fontSize = ((element.font_size || 24) * config.height) / 1920;
                  const actualIndex = selectedLayout.elements.indexOf(element);
                  return (
                    <Group key={elementId}>
                      <Text
                        x={x}
                        y={y}
                        width={width}
                        text={element.text || (element.type === 'headline' ? 'Click to edit' : 'Add text here')}
                        fontSize={fontSize}
                        fill={element.color || '#000000'}
                        fontFamily={element.font_family || 'Arial'}
                        draggable={isDraggable}
                        onClick={() => setSelectedId(elementId)}
                        onTap={() => setSelectedId(elementId)}
                        onDblClick={() => handleTextEdit(actualIndex, element.text || '')}
                        onDblTap={() => handleTextEdit(actualIndex, element.text || '')}
                        onDragEnd={(e) => handleDragEnd(index + 1, e)}
                      />
                      {selectedId === elementId && (
                        <Rect
                          x={x - 2}
                          y={y - 2}
                          width={width + 4}
                          height={fontSize * 1.5}
                          stroke="#3B82F6"
                          strokeWidth={2}
                          dash={[5, 5]}
                          fill="transparent"
                        />
                      )}
                    </Group>
                  );
                }

                if (element.type === 'tesco_tag') {
                  return (
                    <Group key={elementId}>
                      <Rect x={x} y={y} width={width} height={height} fill="#00539F" />
                      <Text
                        x={x + 5}
                        y={y + height / 4}
                        width={width - 10}
                        text={element.text || 'Available at Tesco'}
                        fontSize={Math.min(height * 0.5, 16)}
                        fill="#FFFFFF"
                        align="center"
                      />
                    </Group>
                  );
                }

                if (element.type === 'value_tile') {
                  return (
                    <Group key={elementId}>
                      <Rect x={x} y={y} width={width} height={height} fill="#FFD100" />
                      {element.text && (
                        <Text
                          x={x + 5}
                          y={y + 5}
                          width={width - 10}
                          text={element.text}
                          fontSize={height * 0.4}
                          fill="#000000"
                        />
                      )}
                    </Group>
                  );
                }

                if (element.type === 'drinkaware') {
                  return (
                    <Text
                      key={elementId}
                      x={x}
                      y={y}
                      width={width}
                      text="drinkaware.co.uk"
                      fontSize={height * 0.6}
                      fill={element.color || '#000000'}
                      align="center"
                    />
                  );
                }

                return null;
              })}
          </Layer>
        </Stage>
      </div>

      {/* Text Editing Overlay */}
      {editingText && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 shadow-2xl w-96">
            <h3 className="text-lg font-semibold mb-4">Edit Text</h3>
            <input
              type="text"
              value={editingText.text}
              onChange={handleTextChange}
              onKeyDown={(e) => e.key === 'Enter' && handleTextSave()}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              autoFocus
              placeholder="Enter your text..."
            />
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleTextSave}
                className="flex-1 bg-primary-600 text-white py-2 rounded-lg hover:bg-primary-700"
              >
                Save
              </button>
              <button
                onClick={() => setEditingText(null)}
                className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="absolute bottom-4 left-4 bg-white/90 rounded-lg px-3 py-2 text-xs text-gray-600 shadow-sm">
        <span className="font-medium">Tips:</span> Drag elements to move • Double-click text to edit • Upload assets on the left
      </div>
    </div>
  );
};

export default CanvasEditor;
