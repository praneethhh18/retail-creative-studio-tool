import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from './index';

describe('Store', () => {
  beforeEach(() => {
    // Reset store between tests
    const store = useStore.getState();
    store.setLayout(null);
    store.setSuggestions([]);
    store.setValidationResult(null);
    store.setSelectedChannel('facebook_feed');
    store.setIsLoading(false);
  });

  describe('layout management', () => {
    it('should set layout', () => {
      const store = useStore.getState();
      const layout = {
        elements: [{ id: '1', type: 'text', x: 10, y: 10, width: 50, height: 20 }],
        background_color: '#ffffff',
      };

      store.setLayout(layout as any);
      expect(useStore.getState().layout).toEqual(layout);
    });

    it('should update element', () => {
      const store = useStore.getState();
      store.setLayout({
        elements: [{ id: '1', type: 'text', x: 10, y: 10, width: 50, height: 20 }],
        background_color: '#ffffff',
      } as any);

      store.updateElement('1', { x: 20 });
      expect(useStore.getState().layout?.elements[0].x).toBe(20);
    });

    it('should add element', () => {
      const store = useStore.getState();
      store.setLayout({ elements: [], background_color: '#ffffff' } as any);

      const newElement = { id: '2', type: 'image', x: 0, y: 0, width: 100, height: 100 };
      store.addElement(newElement as any);

      expect(useStore.getState().layout?.elements).toHaveLength(1);
    });

    it('should remove element', () => {
      const store = useStore.getState();
      store.setLayout({
        elements: [
          { id: '1', type: 'text', x: 10, y: 10, width: 50, height: 20 },
          { id: '2', type: 'image', x: 0, y: 0, width: 100, height: 100 },
        ],
        background_color: '#ffffff',
      } as any);

      store.removeElement('1');
      expect(useStore.getState().layout?.elements).toHaveLength(1);
      expect((useStore.getState().layout?.elements[0] as any).id).toBe('2');
    });
  });

  describe('undo/redo', () => {
    it('should track history', () => {
      const store = useStore.getState();
      store.setLayout({ elements: [], background_color: '#ffffff' } as any);

      const element1 = { id: '1', type: 'text', x: 10, y: 10, width: 50, height: 20 };
      store.addElement(element1 as any);

      expect(store.canUndo()).toBe(true);
    });

    it('should undo changes', () => {
      const store = useStore.getState();
      store.setLayout({ elements: [], background_color: '#ffffff' } as any);

      const element1 = { id: '1', type: 'text', x: 10, y: 10, width: 50, height: 20 };
      store.addElement(element1 as any);

      expect(useStore.getState().layout?.elements).toHaveLength(1);

      store.undo();
      expect(useStore.getState().layout?.elements).toHaveLength(0);
    });

    it('should redo changes', () => {
      const store = useStore.getState();
      store.setLayout({ elements: [], background_color: '#ffffff' } as any);

      const element1 = { id: '1', type: 'text', x: 10, y: 10, width: 50, height: 20 };
      store.addElement(element1 as any);
      store.undo();

      expect(useStore.getState().layout?.elements).toHaveLength(0);

      store.redo();
      expect(useStore.getState().layout?.elements).toHaveLength(1);
    });
  });

  describe('asset management', () => {
    it('should add asset', () => {
      const store = useStore.getState();
      const asset = {
        id: 'asset-1',
        type: 'packshot',
        originalPath: '/path/to/image.png',
        palette: ['#ff0000'],
        name: 'Test Asset',
      };

      store.addAsset(asset as any);
      expect(useStore.getState().assets).toHaveLength(1);
    });

    it('should remove asset', () => {
      const store = useStore.getState();
      store.addAsset({
        id: 'asset-1',
        type: 'packshot',
        originalPath: '/path/to/image.png',
        palette: ['#ff0000'],
        name: 'Test Asset',
      } as any);

      store.removeAsset('asset-1');
      expect(useStore.getState().assets).toHaveLength(0);
    });
  });

  describe('channel selection', () => {
    it('should change channel', () => {
      const store = useStore.getState();
      store.setSelectedChannel('instagram_story');
      expect(useStore.getState().selectedChannel).toBe('instagram_story');
    });
  });

  describe('suggestions', () => {
    it('should set suggestions', () => {
      const store = useStore.getState();
      const suggestions = [
        { id: '1', layout: { elements: [] }, score: 0.9, reasoning: 'Test' },
      ];

      store.setSuggestions(suggestions as any);
      expect(useStore.getState().suggestions).toHaveLength(1);
    });

    it('should select suggestion', () => {
      const store = useStore.getState();
      const suggestions = [
        {
          id: '1',
          layout: { elements: [{ id: 'e1', type: 'text' }], background_color: '#fff' },
          score: 0.9,
          reasoning: 'Test',
        },
      ];

      store.setSuggestions(suggestions as any);
      store.selectSuggestion('1');

      expect(useStore.getState().layout).toEqual(suggestions[0].layout);
    });
  });
});
