/**
 * Zustand store for application state management
 */
import { create } from 'zustand';
import { 
  Asset, 
  Layout, 
  LayoutElement,
  CanvasSize, 
  ValidationResult,
  LayoutSuggestion
} from '../types';

const MAX_HISTORY = 50;

interface StoreState {
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

  // Layout
  layout: Layout | null;
  setLayout: (layout: Layout | null) => void;
  updateElement: (id: string, updates: Partial<LayoutElement>) => void;
  addElement: (element: LayoutElement) => void;
  removeElement: (id: string) => void;

  // Suggestions
  suggestions: LayoutSuggestion[];
  setSuggestions: (suggestions: LayoutSuggestion[]) => void;
  selectSuggestion: (id: string) => void;

  // Channel
  selectedChannel: string;
  setSelectedChannel: (channel: string) => void;

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
  canUndo: () => boolean;
  canRedo: () => boolean;
  undo: () => void;
  redo: () => void;
}

export const useStore = create<StoreState>((set, get) => ({
  // Assets
  assets: [],
  addAsset: (asset: Asset) => 
    set((state) => ({ assets: [...state.assets, asset] })),
  removeAsset: (id: string) =>
    set((state) => ({ assets: state.assets.filter((a) => a.id !== id) })),

  // Current project
  brand: '',
  headline: '',
  subhead: '',
  isAlcohol: false,
  setBrand: (brand: string) => set({ brand }),
  setHeadline: (headline: string) => set({ headline }),
  setSubhead: (subhead: string) => set({ subhead }),
  setIsAlcohol: (isAlcohol: boolean) => set({ isAlcohol }),

  // Layout - start with a default editable layout
  layout: {
    id: 'default-layout',
    score: 1.0,
    elements: [
      { type: 'background', color: '#FFFFFF' },
      { type: 'headline', text: 'Click to edit headline', x: 10, y: 30, width: 80, height: 15, font_size: 48, color: '#1F2937' },
      { type: 'subhead', text: 'Add your subheadline here', x: 10, y: 48, width: 80, height: 8, font_size: 24, color: '#6B7280' },
      { type: 'tesco_tag', text: 'Available at Tesco', x: 70, y: 85, width: 25, height: 8 },
    ],
  } as Layout,
  setLayout: (layout: Layout | null) => {
    const { history, historyIndex } = get();
    if (layout) {
      // Add to history
      const newHistory = history.slice(0, historyIndex + 1);
      newHistory.push(JSON.parse(JSON.stringify(layout)));
      if (newHistory.length > MAX_HISTORY) {
        newHistory.shift();
      }
      set({ layout, history: newHistory, historyIndex: newHistory.length - 1 });
    } else {
      set({ layout });
    }
  },
  updateElement: (id: string, updates: Partial<LayoutElement>) => {
    const { layout } = get();
    if (!layout) return;
    
    const newElements = layout.elements.map((el) =>
      el.asset === id || (el as any).id === id ? { ...el, ...updates } : el
    );
    const newLayout = { ...layout, elements: newElements };
    get().setLayout(newLayout);
  },
  addElement: (element: LayoutElement) => {
    const { layout } = get();
    if (!layout) return;
    
    const newLayout = { ...layout, elements: [...layout.elements, element] };
    get().setLayout(newLayout);
  },
  removeElement: (id: string) => {
    const { layout } = get();
    if (!layout) return;
    
    const newElements = layout.elements.filter((el) => 
      el.asset !== id && (el as any).id !== id
    );
    const newLayout = { ...layout, elements: newElements };
    get().setLayout(newLayout);
  },

  // Suggestions
  suggestions: [],
  setSuggestions: (suggestions: LayoutSuggestion[]) => set({ suggestions }),
  selectSuggestion: (id: string) => {
    const { suggestions } = get();
    const suggestion = suggestions.find((s) => s.id === id);
    if (suggestion) {
      get().setLayout(suggestion.layout);
    }
  },

  // Channel
  selectedChannel: 'facebook_feed',
  setSelectedChannel: (channel: string) => set({ selectedChannel: channel }),

  // Canvas
  canvasSize: '1080x1920',
  setCanvasSize: (size: CanvasSize) => set({ canvasSize: size }),

  // Validation
  validationResult: null,
  setValidationResult: (result: ValidationResult | null) => 
    set({ validationResult: result }),

  // UI State
  isLoading: false,
  setIsLoading: (loading: boolean) => set({ isLoading: loading }),

  // History for undo/redo - initialize with default layout
  history: [{
    id: 'default-layout',
    score: 1.0,
    elements: [
      { type: 'background', color: '#FFFFFF' },
      { type: 'headline', text: 'Click to edit headline', x: 10, y: 30, width: 80, height: 15, font_size: 48, color: '#1F2937' },
      { type: 'subhead', text: 'Add your subheadline here', x: 10, y: 48, width: 80, height: 8, font_size: 24, color: '#6B7280' },
      { type: 'tesco_tag', text: 'Available at Tesco', x: 70, y: 85, width: 25, height: 8 },
    ],
  }],
  historyIndex: 0,
  canUndo: () => get().historyIndex > 0,
  canRedo: () => get().historyIndex < get().history.length - 1,
  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      set({ 
        historyIndex: newIndex, 
        layout: JSON.parse(JSON.stringify(history[newIndex])) 
      });
    }
  },
  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      set({ 
        historyIndex: newIndex, 
        layout: JSON.parse(JSON.stringify(history[newIndex])) 
      });
    }
  },
}));;

// Selector hooks for specific state slices
export const useAssets = () => useStore((state) => state.assets);
export const useLayout = () => useStore((state) => state.layout);
export const useSuggestions = () => useStore((state) => state.suggestions);
export const useValidation = () => useStore((state) => state.validationResult);
export const useCanvasSize = () => useStore((state) => state.canvasSize);
export const useIsLoading = () => useStore((state) => state.isLoading);
