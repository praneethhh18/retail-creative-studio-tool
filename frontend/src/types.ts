/**
 * TypeScript type definitions for the Retail Media Creative Tool
 */

// Layout element types
export type ElementType = 
  | 'background'
  | 'packshot'
  | 'logo'
  | 'headline'
  | 'subhead'
  | 'tesco_tag'
  | 'value_tile'
  | 'drinkaware';

export interface LayoutElement {
  type: ElementType;
  asset?: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  z?: number;
  text?: string;
  font_size?: number;
  color?: string;
  font_family?: string;
  rotation?: number;
}

export interface Layout {
  id: string;
  score: number;
  elements: LayoutElement[];
}

export interface LayoutSuggestion {
  id: string;
  layout: Layout;
  score: number;
  reasoning: string;
}

export interface LayoutsResponse {
  layouts: Layout[];
  suggestions?: Layout[];
}

// Upload types
export interface UploadResponse {
  original: string;
  cleaned: string;
  palette: string[];
  asset_id: string;
}

export interface Asset {
  id: string;
  type: 'packshot' | 'logo' | 'background';
  originalPath: string;
  cleanedPath?: string;
  palette: string[];
  name: string;
}

// Generation types
export interface GenRequest {
  packshot_ids?: string[];
  logo_ids?: string[];
  background_id?: string;
  palette?: string[];
  channel?: string;
  user_prompt?: string;
  // Legacy fields
  brand?: string;
  headline?: string;
  subhead?: string;
  colors?: string[];
  packshot_count?: number;
  required_tiles?: {
    tesco_tag: boolean;
    value_tile: boolean;
  };
  canvas?: string;
  is_alcohol?: boolean;
  packshot_assets?: string[];
  logo_asset?: string;
}

// Validation types
export type IssueSeverity = 'hard' | 'warn';

export interface ValidationIssue {
  severity: IssueSeverity;
  code: string;
  message: string;
  fix_suggestion?: string;
  element_id?: string;
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface ValidationResult {
  ok: boolean;
  issues: ValidationIssue[];
  checked_rules: string[];
}

export interface ValidateRequest {
  layout: Layout;
  canvas_size: string;
  is_alcohol: boolean;
  channel: string; // Will be mapped to API channel in client
}

// Export types
export interface ExportRequest {
  layout: Layout;
  assets_map: Record<string, string>;
  sizes: string[];
  format: 'jpeg' | 'png';
  max_file_size_kb: number;
}

export interface ExportedFile {
  channel: string;
  url: string;
  width: number;
  height: number;
  size_kb: number;
  size?: string;
  path?: string;
  format?: string;
  file_size_kb?: number;
}

export interface ExportResponse {
  files: ExportedFile[];
  warnings?: string[];
}

// Canvas types
export type CanvasSize = '1080x1080' | '1080x1920' | '1200x628';

export interface CanvasConfig {
  width: number;
  height: number;
  label: string;
  aspectRatio: string;
}

export const CANVAS_CONFIGS: Record<CanvasSize, CanvasConfig> = {
  '1080x1080': { width: 1080, height: 1080, label: 'Square (1:1)', aspectRatio: '1:1' },
  '1080x1920': { width: 1080, height: 1920, label: 'Stories (9:16)', aspectRatio: '9:16' },
  '1200x628': { width: 1200, height: 628, label: 'Facebook (1.91:1)', aspectRatio: '1.91:1' },
};

// Store types
export interface AppState {
  // Assets
  assets: Asset[];
  addAsset: (asset: Asset) => void;
  removeAsset: (id: string) => void;
  
  // Current project
  brand: string;
  headline: string;
  subhead: string;
  isAlcohol: boolean;
  setBrand: (brand: string) => void;
  setHeadline: (headline: string) => void;
  setSubhead: (subhead: string) => void;
  setIsAlcohol: (isAlcohol: boolean) => void;
  
  // Layouts
  layouts: Layout[];
  selectedLayout: Layout | null;
  setLayouts: (layouts: Layout[]) => void;
  selectLayout: (layout: Layout | null) => void;
  updateLayout: (layout: Layout) => void;
  
  // Canvas
  canvasSize: CanvasSize;
  setCanvasSize: (size: CanvasSize) => void;
  
  // Validation
  validationResult: ValidationResult | null;
  setValidationResult: (result: ValidationResult | null) => void;
  
  // UI State
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  
  // History for undo/redo
  history: Layout[];
  historyIndex: number;
  pushHistory: (layout: Layout) => void;
  undo: () => void;
  redo: () => void;
}

// API Response types
export interface HealthResponse {
  status: string;
  version: string;
  services: {
    llm_available: boolean;
    llm_provider: string;
    bg_removal_available: boolean;
  };
}

export interface CopyModerationResult {
  ok: boolean;
  issues: Array<{
    code: string;
    message: string;
  }>;
}

// Validation Rule info
export interface ValidationRule {
  code: string;
  severity: IssueSeverity;
  description: string;
}
