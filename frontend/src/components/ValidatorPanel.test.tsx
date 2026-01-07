import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ValidatorPanel } from '../components/ValidatorPanel';
import { useStore } from '../store';

// Mock the store
vi.mock('../store', () => ({
  useStore: vi.fn(),
}));

describe('ValidatorPanel', () => {
  beforeEach(() => {
    vi.mocked(useStore).mockReturnValue({
      validationResult: null,
      layout: null,
      setLayout: vi.fn(),
      setValidationResult: vi.fn(),
    } as any);
  });

  it('should render empty state when no validation', () => {
    render(<ValidatorPanel />);
    expect(screen.getByText('Validator')).toBeInTheDocument();
  });

  it('should show issues when validation has errors', () => {
    vi.mocked(useStore).mockReturnValue({
      validationResult: {
        valid: false,
        issues: [
          {
            code: 'SAFE_ZONE',
            severity: 'error',
            message: 'Element outside safe zone',
            element_id: 'elem-1',
            auto_fixable: true,
          },
        ],
      },
      layout: { elements: [] },
      setLayout: vi.fn(),
      setValidationResult: vi.fn(),
    } as any);

    render(<ValidatorPanel />);
    expect(screen.getByText(/Element outside safe zone/)).toBeInTheDocument();
  });

  it('should show passed state when all valid', () => {
    vi.mocked(useStore).mockReturnValue({
      validationResult: {
        valid: true,
        issues: [],
      },
      layout: { elements: [] },
      setLayout: vi.fn(),
      setValidationResult: vi.fn(),
    } as any);

    render(<ValidatorPanel />);
    expect(screen.getByText(/All checks passed/)).toBeInTheDocument();
  });
});
