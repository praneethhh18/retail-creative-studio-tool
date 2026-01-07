/**
 * Smart Canvas - Advanced editing features
 * Provides snapping, guidelines, rotation, and intelligent assistance
 */

// Snap configuration
export const SNAP_CONFIG = {
  enabled: true,
  threshold: 10, // pixels
  gridSize: 20, // pixels
  showGuides: true,
};

// Safe zones configuration by format
export const SAFE_ZONES: Record<string, { top: number; bottom: number; left: number; right: number }> = {
  '1080x1920': { top: 200, bottom: 250, left: 0, right: 0 }, // Stories
  '1080x1080': { top: 0, bottom: 0, left: 0, right: 0 }, // Square
  '1200x628': { top: 0, bottom: 0, left: 0, right: 0 }, // Landscape
};

// Snap point types
export type SnapPoint = {
  x?: number;
  y?: number;
  type: 'edge' | 'center' | 'guide' | 'element' | 'safe-zone';
};

/**
 * Calculate snap points from all elements
 */
export function getSnapPoints(
  elements: Array<{ x?: number; y?: number; width?: number; height?: number; type: string }>,
  canvasWidth: number,
  canvasHeight: number,
  excludeIndex?: number
): SnapPoint[] {
  const points: SnapPoint[] = [];
  
  // Canvas center
  points.push({ x: canvasWidth / 2, type: 'center' });
  points.push({ y: canvasHeight / 2, type: 'center' });
  
  // Canvas edges with margin
  const margin = canvasWidth * 0.05; // 5% margin
  points.push({ x: margin, type: 'guide' });
  points.push({ x: canvasWidth - margin, type: 'guide' });
  points.push({ y: margin, type: 'guide' });
  points.push({ y: canvasHeight - margin, type: 'guide' });
  
  // Safe zones
  const safeZone = SAFE_ZONES['1080x1920'];
  if (safeZone) {
    points.push({ y: safeZone.top, type: 'safe-zone' });
    points.push({ y: canvasHeight - safeZone.bottom, type: 'safe-zone' });
  }
  
  // Element edges
  elements.forEach((elem, index) => {
    if (index === excludeIndex || elem.type === 'background') return;
    if (elem.x === undefined || elem.y === undefined) return;
    
    const x = (elem.x / 100) * canvasWidth;
    const y = (elem.y / 100) * canvasHeight;
    const w = ((elem.width || 0) / 100) * canvasWidth;
    const h = ((elem.height || 0) / 100) * canvasHeight;
    
    // Left, center, right
    points.push({ x, type: 'element' });
    points.push({ x: x + w / 2, type: 'element' });
    points.push({ x: x + w, type: 'element' });
    
    // Top, center, bottom
    points.push({ y, type: 'element' });
    points.push({ y: y + h / 2, type: 'element' });
    points.push({ y: y + h, type: 'element' });
  });
  
  return points;
}

/**
 * Find nearest snap point within threshold
 */
export function findSnapPosition(
  currentX: number,
  currentY: number,
  elementWidth: number,
  elementHeight: number,
  snapPoints: SnapPoint[],
  threshold: number = SNAP_CONFIG.threshold
): { x: number; y: number; snappedX?: number; snappedY?: number } {
  let finalX = currentX;
  let finalY = currentY;
  let snappedX: number | undefined;
  let snappedY: number | undefined;
  
  const elementCenterX = currentX + elementWidth / 2;
  const elementCenterY = currentY + elementHeight / 2;
  const elementRight = currentX + elementWidth;
  const elementBottom = currentY + elementHeight;
  
  // Check X snap points
  for (const point of snapPoints) {
    if (point.x !== undefined) {
      // Check left edge
      if (Math.abs(currentX - point.x) < threshold) {
        finalX = point.x;
        snappedX = point.x;
        break;
      }
      // Check center
      if (Math.abs(elementCenterX - point.x) < threshold) {
        finalX = point.x - elementWidth / 2;
        snappedX = point.x;
        break;
      }
      // Check right edge
      if (Math.abs(elementRight - point.x) < threshold) {
        finalX = point.x - elementWidth;
        snappedX = point.x;
        break;
      }
    }
  }
  
  // Check Y snap points
  for (const point of snapPoints) {
    if (point.y !== undefined) {
      // Check top edge
      if (Math.abs(currentY - point.y) < threshold) {
        finalY = point.y;
        snappedY = point.y;
        break;
      }
      // Check center
      if (Math.abs(elementCenterY - point.y) < threshold) {
        finalY = point.y - elementHeight / 2;
        snappedY = point.y;
        break;
      }
      // Check bottom edge
      if (Math.abs(elementBottom - point.y) < threshold) {
        finalY = point.y - elementHeight;
        snappedY = point.y;
        break;
      }
    }
  }
  
  return { x: finalX, y: finalY, snappedX, snappedY };
}

/**
 * Calculate contrast ratio between two colors
 */
export function calculateContrastRatio(color1: string, color2: string): number {
  const getLuminance = (hex: string): number => {
    const rgb = hex.replace('#', '').match(/.{2}/g)?.map(x => parseInt(x, 16) / 255) || [0, 0, 0];
    const [r, g, b] = rgb.map(c => c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  
  const l1 = getLuminance(color1);
  const l2 = getLuminance(color2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if contrast meets WCAG AA
 */
export function meetsWCAGAA(textColor: string, bgColor: string, fontSize: number): boolean {
  const ratio = calculateContrastRatio(textColor, bgColor);
  // Large text (18pt+ or 14pt bold) needs 3:1, normal text needs 4.5:1
  const required = fontSize >= 24 ? 3 : 4.5;
  return ratio >= required;
}

/**
 * Suggest color for better contrast
 */
export function suggestContrastColor(bgColor: string): string {
  const getLuminance = (hex: string): number => {
    const rgb = hex.replace('#', '').match(/.{2}/g)?.map(x => parseInt(x, 16) / 255) || [0, 0, 0];
    const [r, g, b] = rgb.map(c => c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  
  return getLuminance(bgColor) > 0.5 ? '#000000' : '#FFFFFF';
}

/**
 * Keyboard shortcut definitions
 */
export const KEYBOARD_SHORTCUTS = {
  undo: { key: 'z', ctrl: true, description: 'Undo' },
  redo: { key: 'y', ctrl: true, description: 'Redo' },
  delete: { key: 'Delete', ctrl: false, description: 'Delete selected' },
  duplicate: { key: 'd', ctrl: true, description: 'Duplicate selected' },
  selectAll: { key: 'a', ctrl: true, description: 'Select all' },
  deselect: { key: 'Escape', ctrl: false, description: 'Deselect' },
  moveUp: { key: 'ArrowUp', ctrl: false, description: 'Move up 1px' },
  moveDown: { key: 'ArrowDown', ctrl: false, description: 'Move down 1px' },
  moveLeft: { key: 'ArrowLeft', ctrl: false, description: 'Move left 1px' },
  moveRight: { key: 'ArrowRight', ctrl: false, description: 'Move right 1px' },
  moveUpLarge: { key: 'ArrowUp', shift: true, description: 'Move up 10px' },
  moveDownLarge: { key: 'ArrowDown', shift: true, description: 'Move down 10px' },
  moveLeftLarge: { key: 'ArrowLeft', shift: true, description: 'Move left 10px' },
  moveRightLarge: { key: 'ArrowRight', shift: true, description: 'Move right 10px' },
  bringForward: { key: ']', ctrl: true, description: 'Bring forward' },
  sendBackward: { key: '[', ctrl: true, description: 'Send backward' },
  export: { key: 'e', ctrl: true, description: 'Export' },
  validate: { key: 'Enter', ctrl: true, description: 'Validate' },
};

/**
 * Layout presets for quick starts
 */
export const LAYOUT_PRESETS = {
  'hero-centered': {
    name: 'Hero Centered',
    description: 'Large product image centered with headline below',
    elements: [
      { type: 'packshot', x: 20, y: 20, width: 60, height: 45 },
      { type: 'headline', x: 10, y: 70, width: 80, height: 10 },
      { type: 'tesco_tag', x: 5, y: 85, width: 25, height: 5 },
    ],
  },
  'split-vertical': {
    name: 'Split Vertical',
    description: 'Image on top, text on bottom',
    elements: [
      { type: 'packshot', x: 15, y: 15, width: 70, height: 40 },
      { type: 'headline', x: 10, y: 58, width: 80, height: 10 },
      { type: 'subhead', x: 10, y: 70, width: 80, height: 6 },
      { type: 'tesco_tag', x: 5, y: 85, width: 25, height: 5 },
    ],
  },
  'text-overlay': {
    name: 'Text Overlay',
    description: 'Text overlaid on product image',
    elements: [
      { type: 'packshot', x: 10, y: 10, width: 80, height: 60 },
      { type: 'headline', x: 10, y: 65, width: 80, height: 10, color: '#FFFFFF' },
      { type: 'logo', x: 5, y: 5, width: 15, height: 8 },
      { type: 'tesco_tag', x: 5, y: 85, width: 25, height: 5 },
    ],
  },
  'multi-product': {
    name: 'Multi Product',
    description: 'Multiple products side by side',
    elements: [
      { type: 'packshot', x: 5, y: 25, width: 28, height: 35 },
      { type: 'packshot', x: 36, y: 25, width: 28, height: 35 },
      { type: 'packshot', x: 67, y: 25, width: 28, height: 35 },
      { type: 'headline', x: 10, y: 65, width: 80, height: 10 },
      { type: 'tesco_tag', x: 5, y: 85, width: 25, height: 5 },
    ],
  },
  'alcohol-compliant': {
    name: 'Alcohol Compliant',
    description: 'Pre-configured with Drinkaware',
    elements: [
      { type: 'packshot', x: 25, y: 20, width: 50, height: 40 },
      { type: 'headline', x: 10, y: 62, width: 80, height: 8 },
      { type: 'tesco_tag', x: 5, y: 75, width: 25, height: 5 },
      { type: 'drinkaware', x: 35, y: 92, width: 30, height: 3, color: '#000000' },
    ],
  },
};

export type LayoutPresetKey = keyof typeof LAYOUT_PRESETS;
