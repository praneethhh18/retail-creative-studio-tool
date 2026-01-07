/**
 * Creative Canvas Component
 * Canva-style interactive canvas with smooth animations and inline editing
 */
import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Stage, Layer, Rect, Text, Image as KonvaImage, Transformer, Group, Line } from 'react-konva';
import Konva from 'konva';
import { useStore } from '../store';
import { Layout, LayoutElement, CANVAS_CONFIGS } from '../types';
import { getAssetUrl, validateLayout } from '../api';

// Constants
const SNAP_THRESHOLD = 10;
const SAFE_ZONE_TOP = 200; // pixels for 1920 height
const SAFE_ZONE_BOTTOM = 250;

// Helper functions
const pctToPx = (pct: number, total: number): number => (pct / 100) * total;
const pxToPct = (px: number, total: number): number => (px / total) * 100;

// Floating Toolbar Component
interface FloatingToolbarProps {
  x: number;
  y: number;
  onDuplicate: () => void;
  onDelete: () => void;
  onBringForward: () => void;
  onSendBackward: () => void;
  onCrop?: () => void;
  elementType: string;
  showCrop?: boolean;
}

const FloatingToolbar: React.FC<FloatingToolbarProps> = ({
  x, y, onDuplicate, onDelete, onBringForward, onSendBackward, onCrop, elementType, showCrop
}) => {
  return (
    <div 
      className="absolute bg-white rounded-xl shadow-2xl border border-gray-100 p-1.5 flex gap-1 z-50 animate-fade-in"
      style={{ 
        left: x, 
        top: Math.max(10, y - 50),
        transform: 'translateX(-50%)',
      }}
    >
      {/* Crop button - only for images */}
      {showCrop && onCrop && (
        <>
          <button
            onClick={onCrop}
            className="p-2 hover:bg-blue-50 rounded-lg transition-colors group"
            title="Crop Image"
          >
            <svg className="w-4 h-4 text-gray-600 group-hover:text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4M4 12h16" />
            </svg>
          </button>
          <div className="w-px bg-gray-200 mx-1" />
        </>
      )}
      <button
        onClick={onBringForward}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors group"
        title="Bring Forward"
      >
        <svg className="w-4 h-4 text-gray-600 group-hover:text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      </button>
      <button
        onClick={onSendBackward}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors group"
        title="Send Backward"
      >
        <svg className="w-4 h-4 text-gray-600 group-hover:text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div className="w-px bg-gray-200 mx-1" />
      <button
        onClick={onDuplicate}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors group"
        title="Duplicate"
      >
        <svg className="w-4 h-4 text-gray-600 group-hover:text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      </button>
      <button
        onClick={onDelete}
        className="p-2 hover:bg-red-50 rounded-lg transition-colors group"
        title="Delete"
      >
        <svg className="w-4 h-4 text-gray-600 group-hover:text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  );
};

// Inline Text Editor
interface InlineTextEditorProps {
  x: number;
  y: number;
  width: number;
  value: string;
  fontSize: number;
  color: string;
  onSave: (text: string) => void;
  onCancel: () => void;
}

const InlineTextEditor: React.FC<InlineTextEditorProps> = ({
  x, y, width, value, fontSize, color, onSave, onCancel
}) => {
  const [text, setText] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSave(text);
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  return (
    <input
      ref={inputRef}
      type="text"
      value={text}
      onChange={(e) => setText(e.target.value)}
      onKeyDown={handleKeyDown}
      onBlur={() => onSave(text)}
      className="absolute bg-transparent border-2 border-primary-500 rounded px-2 outline-none"
      style={{
        left: x,
        top: y,
        width: Math.max(width, 200),
        fontSize: fontSize,
        color: color,
        fontFamily: 'Arial',
        lineHeight: 1.2,
      }}
    />
  );
};

// Design Tools Panel - Simplified and clean
interface DesignToolsProps {
  bgColor: string;
  onBgColorChange: (color: string) => void;
  palette: string[];
}

const DesignTools: React.FC<DesignToolsProps> = ({
  bgColor, onBgColorChange, palette
}) => {
  const presetColors = ['#FFFFFF', '#F3F4F6', '#1F2937', '#374151', '#DC2626', '#059669', '#2563EB', '#7C3AED'];
  const allColors = [...new Set([...palette.filter(c => c), ...presetColors])].slice(0, 8);

  return (
    <div className="absolute top-4 left-4 bg-white rounded-xl shadow-lg border border-gray-200 p-3 z-20 w-56">
      {/* Background */}
      <div className="mb-3">
        <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Background</label>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {allColors.map((color) => (
            <button
              key={color}
              onClick={() => onBgColorChange(color)}
              className={`w-7 h-7 rounded-md border-2 transition-all hover:scale-110 ${
                bgColor === color ? 'border-blue-500 shadow-md' : 'border-gray-200'
              }`}
              style={{ backgroundColor: color }}
              title={color}
            />
          ))}
          <label className="w-7 h-7 rounded-md border-2 border-dashed border-gray-300 flex items-center justify-center cursor-pointer hover:border-blue-400" title="Custom color">
            <input
              type="color"
              value={bgColor}
              onChange={(e) => onBgColorChange(e.target.value)}
              className="opacity-0 absolute w-0 h-0"
            />
            <span className="text-gray-400 text-xs">+</span>
          </label>
        </div>
      </div>

      {/* Quick Add - Simplified */}
      <div className="pt-3 border-t border-gray-100">
        <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Quick Add</label>
        <div className="flex gap-2 mt-2">
          <button
            onClick={() => {
              const event = new CustomEvent('addElement', { detail: { type: 'headline' } });
              window.dispatchEvent(event);
            }}
            className="flex-1 px-2 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-xs font-medium transition-colors"
          >
            + Headline
          </button>
          <button
            onClick={() => {
              const event = new CustomEvent('addElement', { detail: { type: 'subhead' } });
              window.dispatchEvent(event);
            }}
            className="flex-1 px-2 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-xs font-medium transition-colors"
          >
            + Subhead
          </button>
        </div>
      </div>
    </div>
  );
};

// Background Image Component (full canvas size, no interaction)
interface BackgroundImageProps {
  src: string;
  width: number;
  height: number;
}

const BackgroundImage: React.FC<BackgroundImageProps> = ({ src, width, height }) => {
  const assetUrl = getAssetUrl(src);
  const [image, setImage] = useState<HTMLImageElement | null>(null);

  useEffect(() => {
    if (!assetUrl) return;
    const img = new window.Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => setImage(img);
    img.src = assetUrl;
    return () => { img.onload = null; };
  }, [assetUrl]);

  if (!image) return null;

  return (
    <KonvaImage
      image={image}
      x={0}
      y={0}
      width={width}
      height={height}
      listening={false}
    />
  );
};

// Asset Image Component with smooth loading
interface AssetImageProps {
  src: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation?: number;
  draggable: boolean;
  isSelected: boolean;
  onSelect: () => void;
  onDragStart?: () => void;
  onDragEnd: (x: number, y: number) => void;
  onTransform?: (width: number, height: number, rotation: number) => void;
}

const AssetImage: React.FC<AssetImageProps> = ({
  src, x, y, width, height, rotation = 0, draggable, isSelected, onSelect, onDragStart, onDragEnd, onTransform
}) => {
  const assetUrl = getAssetUrl(src);
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [status, setStatus] = useState<'loading' | 'loaded' | 'failed'>('loading');
  const shapeRef = useRef<Konva.Image>(null);
  const trRef = useRef<Konva.Transformer>(null);

  useEffect(() => {
    if (!assetUrl) {
      setStatus('failed');
      return;
    }
    const img = new window.Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => { setImage(img); setStatus('loaded'); };
    img.onerror = () => setStatus('failed');
    img.src = assetUrl;
    return () => { img.onload = null; img.onerror = null; };
  }, [assetUrl]);

  useEffect(() => {
    if (isSelected && trRef.current && shapeRef.current) {
      trRef.current.nodes([shapeRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, [isSelected]);

  const handleTransformEnd = () => {
    const node = shapeRef.current;
    if (!node || !onTransform) return;
    
    const scaleX = node.scaleX();
    const scaleY = node.scaleY();
    
    node.scaleX(1);
    node.scaleY(1);
    
    onTransform(
      node.width() * scaleX,
      node.height() * scaleY,
      node.rotation()
    );
  };

  if (status === 'loading') {
    return (
      <Group>
        <Rect x={x} y={y} width={width} height={height} fill="#f3f4f6" cornerRadius={8} />
        <Text x={x} y={y + height/2 - 10} width={width} text="Loading..." align="center" fill="#9ca3af" fontSize={14} />
      </Group>
    );
  }

  if (status === 'failed' || !image) {
    return (
      <Group>
        <Rect x={x} y={y} width={width} height={height} fill="#fef2f2" stroke="#fca5a5" strokeWidth={2} cornerRadius={8} />
        <Text x={x} y={y + height/2 - 10} width={width} text="⚠️ Image" align="center" fill="#ef4444" fontSize={14} />
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
        rotation={rotation}
        draggable={draggable}
        onClick={onSelect}
        onTap={onSelect}
        onDragStart={onDragStart}
        onDragEnd={(e) => onDragEnd(e.target.x(), e.target.y())}
        onTransformEnd={handleTransformEnd}
      />
      {isSelected && (
        <Transformer
          ref={trRef}
          rotateEnabled={true}
          enabledAnchors={['top-left', 'top-center', 'top-right', 'middle-left', 'middle-right', 'bottom-left', 'bottom-center', 'bottom-right']}
          boundBoxFunc={(oldBox, newBox) => {
            if (newBox.width < 20 || newBox.height < 20) return oldBox;
            return newBox;
          }}
          borderStroke="#3B82F6"
          borderStrokeWidth={2}
          anchorFill="#ffffff"
          anchorStroke="#3B82F6"
          anchorSize={10}
          anchorCornerRadius={3}
          keepRatio={false}
        />
      )}
    </>
  );
};

// Main Creative Canvas Component
interface CreativeCanvasProps {
  onLayoutChange?: (layout: Layout) => void;
}

export const CreativeCanvas: React.FC<CreativeCanvasProps> = ({ onLayoutChange }) => {
  const { layout, setLayout, canvasSize, isAlcohol, setValidationResult, assets } = useStore();
  const stageRef = useRef<Konva.Stage>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [scale, setScale] = useState(1);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [editingTextIndex, setEditingTextIndex] = useState<number | null>(null);
  const [showSnapLines, setShowSnapLines] = useState<{ x: number | null; y: number | null }>({ x: null, y: null });
  const [toolbarPosition, setToolbarPosition] = useState<{ x: number; y: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [cropMode, setCropMode] = useState<number | null>(null); // Index of element being cropped
  const [cropRect, setCropRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null);

  const config = CANVAS_CONFIGS[canvasSize];
  const palette = assets[0]?.palette || ['#FFFFFF', '#000000'];

  // Update scale on resize
  useEffect(() => {
    const updateScale = () => {
      if (!containerRef.current) return;
      const containerWidth = containerRef.current.clientWidth - 80;
      const containerHeight = containerRef.current.clientHeight - 80;
      const scaleX = containerWidth / config.width;
      const scaleY = containerHeight / config.height;
      setScale(Math.min(scaleX, scaleY, 1));
    };
    updateScale();
    window.addEventListener('resize', updateScale);
    return () => window.removeEventListener('resize', updateScale);
  }, [config.width, config.height]);

  // Listen for add element events
  useEffect(() => {
    const handleAddElement = (e: CustomEvent) => {
      if (!layout) return;
      const { type } = e.detail;
      const newElement: LayoutElement = type === 'headline' 
        ? { type: 'headline', text: 'New Headline', x: 10, y: 30, width: 80, height: 12, font_size: 48, color: '#1F2937' }
        : { type: 'subhead', text: 'Add your text here', x: 10, y: 45, width: 80, height: 8, font_size: 24, color: '#6B7280' };
      
      const newLayout = { ...layout, elements: [...layout.elements, newElement] };
      setLayout(newLayout);
      setSelectedIndex(newLayout.elements.length - 1);
    };
    window.addEventListener('addElement', handleAddElement as EventListener);
    return () => window.removeEventListener('addElement', handleAddElement as EventListener);
  }, [layout, setLayout]);

  // Background validation (non-blocking)
  const runValidation = useCallback(async (l: Layout) => {
    try {
      const result = await validateLayout({
        layout: l,
        canvas_size: canvasSize,
        is_alcohol: isAlcohol,
        channel: canvasSize === '1080x1920' ? 'stories' : 'facebook',
      });
      setValidationResult(result);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  }, [canvasSize, isAlcohol, setValidationResult]);

  // Update element
  const updateElement = useCallback((index: number, updates: Partial<LayoutElement>) => {
    if (!layout) return;
    const newElements = [...layout.elements];
    newElements[index] = { ...newElements[index], ...updates };
    const newLayout = { ...layout, elements: newElements };
    setLayout(newLayout);
    onLayoutChange?.(newLayout);
    runValidation(newLayout);
  }, [layout, setLayout, onLayoutChange, runValidation]);

  // Handle drag with snapping
  const handleDrag = useCallback((index: number, newX: number, newY: number) => {
    const centerX = config.width / 2;
    const centerY = config.height / 2;
    
    const element = layout?.elements[index];
    if (!element) return { x: newX, y: newY };
    
    const elemWidth = pctToPx(element.width || 20, config.width);
    const elemHeight = pctToPx(element.height || 10, config.height);
    const elemCenterX = newX + elemWidth / 2;
    const elemCenterY = newY + elemHeight / 2;
    
    let snapX: number | null = null;
    let snapY: number | null = null;
    let finalX = newX;
    let finalY = newY;
    
    // Snap to center
    if (Math.abs(elemCenterX - centerX) < SNAP_THRESHOLD) {
      finalX = centerX - elemWidth / 2;
      snapX = centerX;
    }
    if (Math.abs(elemCenterY - centerY) < SNAP_THRESHOLD) {
      finalY = centerY - elemHeight / 2;
      snapY = centerY;
    }
    
    // Snap to edges
    if (Math.abs(newX) < SNAP_THRESHOLD) { finalX = 0; snapX = 0; }
    if (Math.abs(newY) < SNAP_THRESHOLD) { finalY = 0; snapY = 0; }
    if (Math.abs(newX + elemWidth - config.width) < SNAP_THRESHOLD) { finalX = config.width - elemWidth; snapX = config.width; }
    if (Math.abs(newY + elemHeight - config.height) < SNAP_THRESHOLD) { finalY = config.height - elemHeight; snapY = config.height; }
    
    setShowSnapLines({ x: snapX, y: snapY });
    return { x: finalX, y: finalY };
  }, [config.width, config.height, layout?.elements]);

  // Handle drag end
  const handleDragEnd = useCallback((index: number, x: number, y: number) => {
    const snapped = handleDrag(index, x, y);
    updateElement(index, {
      x: pxToPct(snapped.x, config.width),
      y: pxToPct(snapped.y, config.height),
    });
    setShowSnapLines({ x: null, y: null });
    setIsDragging(false);
  }, [handleDrag, updateElement, config.width, config.height]);

  // Handle transform (resize/rotate)
  const handleTransform = useCallback((index: number, width: number, height: number, rotation: number) => {
    updateElement(index, {
      width: pxToPct(width, config.width),
      height: pxToPct(height, config.height),
      rotation,
    });
  }, [updateElement, config.width, config.height]);

  // Element actions
  const duplicateElement = useCallback(() => {
    if (selectedIndex === null || !layout) return;
    const element = layout.elements[selectedIndex];
    const newElement = { ...element, x: (element.x || 0) + 5, y: (element.y || 0) + 5 };
    const newLayout = { ...layout, elements: [...layout.elements, newElement] };
    setLayout(newLayout);
    setSelectedIndex(newLayout.elements.length - 1);
  }, [selectedIndex, layout, setLayout]);

  const deleteElement = useCallback(() => {
    if (selectedIndex === null || !layout) return;
    const element = layout.elements[selectedIndex];
    // Don't allow deleting background
    if (element.type === 'background') return;
    const newElements = layout.elements.filter((_, i) => i !== selectedIndex);
    setLayout({ ...layout, elements: newElements });
    setSelectedIndex(null);
    setToolbarPosition(null);
  }, [selectedIndex, layout, setLayout]);

  const changeLayer = useCallback((direction: 'up' | 'down') => {
    if (selectedIndex === null || !layout) return;
    const element = layout.elements[selectedIndex];
    const currentZ = element.z || 0;
    updateElement(selectedIndex, { z: direction === 'up' ? currentZ + 1 : currentZ - 1 });
  }, [selectedIndex, layout, updateElement]);

  // Start crop mode for the selected element
  const startCrop = useCallback(() => {
    if (selectedIndex === null || !layout) return;
    const element = layout.elements[selectedIndex];
    if (element.type !== 'packshot' && element.type !== 'logo') return;
    
    setCropMode(selectedIndex);
    // Initialize crop rect to full element
    setCropRect({
      x: pctToPx(element.x || 0, config.width),
      y: pctToPx(element.y || 0, config.height),
      width: pctToPx(element.width || 20, config.width),
      height: pctToPx(element.height || 20, config.height),
    });
  }, [selectedIndex, layout, config]);

  // Apply crop
  const applyCrop = useCallback(() => {
    if (cropMode === null || !cropRect || !layout) return;
    
    // Convert crop rect back to percentages and update element
    updateElement(cropMode, {
      x: pxToPct(cropRect.x, config.width),
      y: pxToPct(cropRect.y, config.height),
      width: pxToPct(cropRect.width, config.width),
      height: pxToPct(cropRect.height, config.height),
    });
    
    setCropMode(null);
    setCropRect(null);
  }, [cropMode, cropRect, layout, config, updateElement]);

  // Cancel crop
  const cancelCrop = useCallback(() => {
    setCropMode(null);
    setCropRect(null);
  }, []);

  // Deselect on empty click
  const handleStageClick = useCallback((e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.target === e.target.getStage()) {
      setSelectedIndex(null);
      setToolbarPosition(null);
    }
  }, []);

  // Update toolbar position when selection changes
  useEffect(() => {
    if (selectedIndex !== null && layout && !isDragging) {
      const element = layout.elements[selectedIndex];
      const x = pctToPx(element.x || 0, config.width) + pctToPx((element.width || 20) / 2, config.width);
      const y = pctToPx(element.y || 0, config.height);
      setToolbarPosition({
        x: x * scale + (containerRef.current?.offsetLeft || 0) + ((containerRef.current?.clientWidth || 0) - config.width * scale) / 2,
        y: y * scale + (containerRef.current?.offsetTop || 0) + ((containerRef.current?.clientHeight || 0) - config.height * scale) / 2,
      });
    } else {
      setToolbarPosition(null);
    }
  }, [selectedIndex, layout, config, scale, isDragging]);

  // Get background color
  const bgElement = layout?.elements.find((e) => e.type === 'background');
  const bgColor = bgElement?.color || '#FFFFFF';

  const handleBgColorChange = useCallback((color: string) => {
    if (!layout) return;
    const newElements = layout.elements.map((el) => 
      el.type === 'background' ? { ...el, color } : el
    );
    setLayout({ ...layout, elements: newElements });
  }, [layout, setLayout]);

  const selectedElement = selectedIndex !== null ? layout?.elements[selectedIndex] : null;

  if (!layout) {
    return (
      <div className="flex items-center justify-center h-full bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl">
        <div className="text-center p-12">
          <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-primary-400 to-purple-500 rounded-3xl flex items-center justify-center shadow-lg">
            <svg className="w-12 h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="text-2xl font-bold text-gray-800 mb-3">Start Creating</h3>
          <p className="text-gray-500 mb-6 max-w-sm">Upload assets and generate layouts, or start with a blank canvas</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => setLayout({
                id: 'blank-' + Date.now(),
                score: 1,
                elements: [{ type: 'background', color: '#FFFFFF' }]
              })}
              className="px-6 py-3 bg-white border border-gray-200 rounded-xl text-gray-700 font-medium hover:bg-gray-50 transition-colors shadow-sm"
            >
              Blank Canvas
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 via-gray-50 to-gray-100 p-6 relative overflow-hidden">
      {/* Design Tools Panel */}
      <DesignTools
        bgColor={bgColor}
        onBgColorChange={handleBgColorChange}
        palette={palette}
      />

      {/* Floating Toolbar */}
      {toolbarPosition && selectedIndex !== null && !isDragging && selectedElement?.type !== 'background' && cropMode === null && (
        <FloatingToolbar
          x={toolbarPosition.x}
          y={toolbarPosition.y}
          elementType={selectedElement?.type || ''}
          onDuplicate={duplicateElement}
          onDelete={deleteElement}
          onBringForward={() => changeLayer('up')}
          onSendBackward={() => changeLayer('down')}
          onCrop={startCrop}
          showCrop={selectedElement?.type === 'packshot' || selectedElement?.type === 'logo'}
        />
      )}

      {/* Crop Mode UI */}
      {cropMode !== null && cropRect && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-white rounded-xl shadow-2xl p-3 flex gap-2 z-50 animate-fade-in">
          <span className="text-sm text-gray-600 mr-2 self-center">Drag corners to crop</span>
          <button
            onClick={applyCrop}
            className="px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            Apply Crop
          </button>
          <button
            onClick={cancelCrop}
            className="px-4 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Canvas */}
      <div
        className="relative bg-white rounded-lg transition-shadow duration-300"
        style={{
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
          width: config.width * scale,
          height: config.height * scale,
        }}
      >
        <Stage
          ref={stageRef}
          width={config.width * scale}
          height={config.height * scale}
          scaleX={scale}
          scaleY={scale}
          onMouseDown={handleStageClick}
          onTouchStart={(e) => handleStageClick(e as unknown as Konva.KonvaEventObject<MouseEvent>)}
        >
          <Layer>
            {/* Background Color */}
            <Rect x={0} y={0} width={config.width} height={config.height} fill={bgColor} />

            {/* Background Image (if any element has type packshot and z=0, it's a background image) */}
            {layout.elements
              .filter((e) => (e.type === 'packshot' || e.type === 'logo') && (e.z === 0 || e.width === 100))
              .map((element, idx) => (
                element.asset && (
                  <BackgroundImage
                    key={`bg-img-${idx}`}
                    src={element.asset}
                    width={config.width}
                    height={config.height}
                  />
                )
              ))
            }

            {/* Soft Safe Zone Guides (Stories only) */}
            {canvasSize === '1080x1920' && (
              <>
                <Rect
                  x={0}
                  y={0}
                  width={config.width}
                  height={SAFE_ZONE_TOP}
                  fill="rgba(59, 130, 246, 0.05)"
                />
                <Line
                  points={[0, SAFE_ZONE_TOP, config.width, SAFE_ZONE_TOP]}
                  stroke="rgba(59, 130, 246, 0.3)"
                  strokeWidth={1}
                  dash={[8, 8]}
                />
                <Rect
                  x={0}
                  y={config.height - SAFE_ZONE_BOTTOM}
                  width={config.width}
                  height={SAFE_ZONE_BOTTOM}
                  fill="rgba(59, 130, 246, 0.05)"
                />
                <Line
                  points={[0, config.height - SAFE_ZONE_BOTTOM, config.width, config.height - SAFE_ZONE_BOTTOM]}
                  stroke="rgba(59, 130, 246, 0.3)"
                  strokeWidth={1}
                  dash={[8, 8]}
                />
              </>
            )}

            {/* Center guide lines when snapping */}
            {showSnapLines.x !== null && (
              <Line
                points={[showSnapLines.x, 0, showSnapLines.x, config.height]}
                stroke="#3B82F6"
                strokeWidth={1}
                dash={[4, 4]}
              />
            )}
            {showSnapLines.y !== null && (
              <Line
                points={[0, showSnapLines.y, config.width, showSnapLines.y]}
                stroke="#3B82F6"
                strokeWidth={1}
                dash={[4, 4]}
              />
            )}

            {/* Render Elements */}
            {layout.elements
              .filter((e) => e.type !== 'background')
              .filter((e) => !((e.type === 'packshot' || e.type === 'logo') && e.z === 0 && e.width === 100)) // Exclude full-canvas bg images (rendered separately)
              .sort((a, b) => (a.z || 0) - (b.z || 0))
              .map((element, idx) => {
                const elementIndex = layout.elements.indexOf(element);
                const x = pctToPx(element.x || 0, config.width);
                const y = pctToPx(element.y || 0, config.height);
                const width = pctToPx(element.width || 20, config.width);
                const height = pctToPx(element.height || 10, config.height);
                const isSelected = selectedIndex === elementIndex;

                // Packshot / Logo - both rendered as images
                if (element.type === 'packshot' || element.type === 'logo') {
                  console.log(`Rendering ${element.type}:`, element.asset, { x, y, width, height });
                  return (
                    <AssetImage
                      key={`${element.type}-${idx}-${element.asset}`}
                      src={element.asset || ''}
                      x={x}
                      y={y}
                      width={width}
                      height={height}
                      rotation={element.rotation || 0}
                      draggable={true}
                      isSelected={isSelected}
                      onSelect={() => setSelectedIndex(elementIndex)}
                      onDragStart={() => setIsDragging(true)}
                      onDragEnd={(newX, newY) => handleDragEnd(elementIndex, newX, newY)}
                      onTransform={(w, h, r) => handleTransform(elementIndex, w, h, r)}
                    />
                  );
                }

                // Headline / Subhead
                if (element.type === 'headline' || element.type === 'subhead') {
                  const fontSize = ((element.font_size || 24) * config.height) / 1920;
                  return (
                    <Group key={`${element.type}-${idx}`}>
                      <Text
                        x={x}
                        y={y}
                        width={width}
                        text={element.text || 'Click to edit'}
                        fontSize={fontSize}
                        fill={element.color || '#000000'}
                        fontFamily={element.font_family || 'Arial'}
                        fontStyle={element.type === 'headline' ? 'bold' : 'normal'}
                        draggable={true}
                        onClick={() => setSelectedIndex(elementIndex)}
                        onTap={() => setSelectedIndex(elementIndex)}
                        onDblClick={() => setEditingTextIndex(elementIndex)}
                        onDblTap={() => setEditingTextIndex(elementIndex)}
                        onDragStart={() => setIsDragging(true)}
                        onDragEnd={(e) => handleDragEnd(elementIndex, e.target.x(), e.target.y())}
                      />
                      {isSelected && (
                        <Rect
                          x={x - 4}
                          y={y - 4}
                          width={width + 8}
                          height={fontSize * 1.4 + 8}
                          stroke="#3B82F6"
                          strokeWidth={2}
                          cornerRadius={4}
                          fill="transparent"
                        />
                      )}
                    </Group>
                  );
                }

                // Tesco Tag
                if (element.type === 'tesco_tag') {
                  return (
                    <Group key={`tesco-${idx}`}>
                      <Rect x={x} y={y} width={width} height={height} fill="#00539F" cornerRadius={4} />
                      <Text
                        x={x}
                        y={y + height * 0.3}
                        width={width}
                        text={element.text || 'Available at Tesco'}
                        fontSize={height * 0.4}
                        fill="#FFFFFF"
                        align="center"
                        fontStyle="bold"
                      />
                    </Group>
                  );
                }

                // Value Tile
                if (element.type === 'value_tile') {
                  return (
                    <Group key={`value-${idx}`}>
                      <Rect x={x} y={y} width={width} height={height} fill="#FFD100" cornerRadius={4} />
                      <Text
                        x={x}
                        y={y + height * 0.3}
                        width={width}
                        text={element.text || '£XX'}
                        fontSize={height * 0.4}
                        fill="#000000"
                        align="center"
                        fontStyle="bold"
                      />
                    </Group>
                  );
                }

                // Drinkaware
                if (element.type === 'drinkaware') {
                  return (
                    <Text
                      key={`drink-${idx}`}
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

            {/* Crop Overlay */}
            {cropMode !== null && cropRect && (
              <>
                {/* Darkened areas outside crop */}
                <Rect x={0} y={0} width={config.width} height={cropRect.y} fill="rgba(0,0,0,0.5)" />
                <Rect x={0} y={cropRect.y} width={cropRect.x} height={cropRect.height} fill="rgba(0,0,0,0.5)" />
                <Rect x={cropRect.x + cropRect.width} y={cropRect.y} width={config.width - cropRect.x - cropRect.width} height={cropRect.height} fill="rgba(0,0,0,0.5)" />
                <Rect x={0} y={cropRect.y + cropRect.height} width={config.width} height={config.height - cropRect.y - cropRect.height} fill="rgba(0,0,0,0.5)" />
                
                {/* Crop selection rectangle */}
                <Rect
                  x={cropRect.x}
                  y={cropRect.y}
                  width={cropRect.width}
                  height={cropRect.height}
                  stroke="#3B82F6"
                  strokeWidth={2}
                  draggable
                  onDragEnd={(e) => {
                    setCropRect({
                      ...cropRect,
                      x: Math.max(0, Math.min(e.target.x(), config.width - cropRect.width)),
                      y: Math.max(0, Math.min(e.target.y(), config.height - cropRect.height)),
                    });
                  }}
                />
                
                {/* Corner handles */}
                {[
                  { cursor: 'nw-resize', cx: cropRect.x, cy: cropRect.y, dx: -1, dy: -1 },
                  { cursor: 'ne-resize', cx: cropRect.x + cropRect.width, cy: cropRect.y, dx: 1, dy: -1 },
                  { cursor: 'sw-resize', cx: cropRect.x, cy: cropRect.y + cropRect.height, dx: -1, dy: 1 },
                  { cursor: 'se-resize', cx: cropRect.x + cropRect.width, cy: cropRect.y + cropRect.height, dx: 1, dy: 1 },
                ].map((handle, i) => (
                  <Rect
                    key={`crop-handle-${i}`}
                    x={handle.cx - 6}
                    y={handle.cy - 6}
                    width={12}
                    height={12}
                    fill="#3B82F6"
                    cornerRadius={2}
                    draggable
                    onDragMove={(e) => {
                      const newX = e.target.x() + 6;
                      const newY = e.target.y() + 6;
                      let newRect = { ...cropRect };
                      
                      if (handle.dx < 0) {
                        newRect.width = cropRect.x + cropRect.width - newX;
                        newRect.x = newX;
                      } else {
                        newRect.width = newX - cropRect.x;
                      }
                      
                      if (handle.dy < 0) {
                        newRect.height = cropRect.y + cropRect.height - newY;
                        newRect.y = newY;
                      } else {
                        newRect.height = newY - cropRect.y;
                      }
                      
                      // Ensure minimum size
                      if (newRect.width >= 20 && newRect.height >= 20) {
                        setCropRect(newRect);
                      }
                    }}
                    onDragEnd={(e) => {
                      e.target.position({ x: handle.cx - 6, y: handle.cy - 6 });
                    }}
                  />
                ))}
              </>
            )}
          </Layer>
        </Stage>

        {/* Inline Text Editor Overlay */}
        {editingTextIndex !== null && layout.elements[editingTextIndex] && (
          <InlineTextEditor
            x={pctToPx(layout.elements[editingTextIndex].x || 0, config.width) * scale}
            y={pctToPx(layout.elements[editingTextIndex].y || 0, config.height) * scale}
            width={pctToPx(layout.elements[editingTextIndex].width || 80, config.width) * scale}
            value={layout.elements[editingTextIndex].text || ''}
            fontSize={((layout.elements[editingTextIndex].font_size || 24) * config.height / 1920) * scale}
            color={layout.elements[editingTextIndex].color || '#000000'}
            onSave={(text) => {
              updateElement(editingTextIndex, { text });
              setEditingTextIndex(null);
            }}
            onCancel={() => setEditingTextIndex(null)}
          />
        )}
      </div>

      {/* Keyboard shortcuts hint */}
      <div className="absolute bottom-4 right-4 bg-white/80 backdrop-blur-sm rounded-lg px-4 py-2 text-xs text-gray-500">
        <span className="font-medium">Tips:</span> Click to select • Drag to move • Double-click text to edit • Del to delete
      </div>
    </div>
  );
};

export default CreativeCanvas;
