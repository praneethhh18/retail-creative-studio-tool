/**
 * Design Wizard Component
 * Guided creative builder for non-designers
 * Step-by-step process for creating compliant creatives
 */
import React, { useState, useCallback } from 'react';
import clsx from 'clsx';
import { useStore } from '../store';
import { Layout, LayoutElement } from '../types';
import { LAYOUT_PRESETS, LayoutPresetKey } from '../utils/smartCanvas';

interface WizardStep {
  id: string;
  title: string;
  description: string;
}

const WIZARD_STEPS: WizardStep[] = [
  { id: 'assets', title: 'Upload Assets', description: 'Add your product images and logo' },
  { id: 'style', title: 'Choose Style', description: 'Select a layout template' },
  { id: 'content', title: 'Add Content', description: 'Enter your headline and copy' },
  { id: 'customize', title: 'Customize', description: 'Adjust colors and positioning' },
  { id: 'review', title: 'Review & Export', description: 'Validate and download' },
];

interface DesignWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete?: (layout: Layout) => void;
}

export const DesignWizard: React.FC<DesignWizardProps> = ({
  isOpen,
  onClose,
  onComplete,
}) => {
  const { assets, setLayout, canvasSize } = useStore();
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedPreset, setSelectedPreset] = useState<LayoutPresetKey | null>(null);
  const [headline, setHeadline] = useState('');
  const [subhead, setSubhead] = useState('');
  const [selectedColors, setSelectedColors] = useState<string[]>(['#FFFFFF', '#000000']);
  const [isAlcohol, setIsAlcohol] = useState(false);

  const packshots = assets.filter(a => a.type === 'packshot');
  const logos = assets.filter(a => a.type === 'logo');

  const handleNext = useCallback(() => {
    if (currentStep < WIZARD_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  }, [currentStep]);

  const handleBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  }, [currentStep]);

  const generateLayout = useCallback((): Layout => {
    if (!selectedPreset) {
      return {
        id: `wizard-${Date.now()}`,
        score: 0.9,
        elements: [],
      };
    }

    const preset = LAYOUT_PRESETS[selectedPreset];
    const elements: LayoutElement[] = [
      { type: 'background', color: selectedColors[0] || '#FFFFFF' },
    ];

    let packshotIndex = 0;

    preset.elements.forEach(elem => {
      const newElement: LayoutElement = { ...elem } as LayoutElement;

      if (elem.type === 'packshot' && packshots[packshotIndex]) {
        // Use full asset path for proper rendering
        newElement.asset = packshots[packshotIndex].cleanedPath || packshots[packshotIndex].originalPath;
        packshotIndex++;
      } else if (elem.type === 'logo' && logos[0]) {
        // Use full asset path for proper rendering
        newElement.asset = logos[0].cleanedPath || logos[0].originalPath;
      } else if (elem.type === 'headline') {
        newElement.text = headline || 'Your Headline Here';
        newElement.color = selectedColors[1] || '#000000';
        newElement.font_size = 48;
      } else if (elem.type === 'subhead') {
        newElement.text = subhead || '';
        newElement.color = selectedColors[1] || '#000000';
        newElement.font_size = 24;
      } else if (elem.type === 'tesco_tag') {
        newElement.text = 'Available at Tesco';
      }

      elements.push(newElement);
    });

    // Add drinkaware if alcohol
    if (isAlcohol) {
      elements.push({
        type: 'drinkaware',
        x: 35,
        y: 92,
        width: 30,
        height: 3,
        color: '#000000',
      });
    }

    return {
      id: `wizard-${Date.now()}`,
      score: 0.9,
      elements,
    };
  }, [selectedPreset, headline, subhead, selectedColors, packshots, logos, isAlcohol]);

  const handleComplete = useCallback(() => {
    const layout = generateLayout();
    setLayout(layout);
    onComplete?.(layout);
    onClose();
  }, [generateLayout, setLayout, onComplete, onClose]);

  if (!isOpen) return null;

  const renderStepContent = () => {
    switch (WIZARD_STEPS[currentStep].id) {
      case 'assets':
        return (
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Product Images ({packshots.length})</h4>
              {packshots.length === 0 ? (
                <p className="text-sm text-gray-500">
                  Upload product images from the Asset Library on the left
                </p>
              ) : (
                <div className="flex gap-2 flex-wrap">
                  {packshots.map(asset => (
                    <div key={asset.id} className="w-16 h-16 bg-gray-100 rounded overflow-hidden">
                      <img
                        src={asset.cleanedPath || asset.originalPath}
                        alt={asset.name}
                        className="w-full h-full object-contain"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Logo ({logos.length})</h4>
              {logos.length === 0 ? (
                <p className="text-sm text-gray-500">Optional: Add your brand logo</p>
              ) : (
                <div className="flex gap-2">
                  {logos.map(asset => (
                    <div key={asset.id} className="w-16 h-16 bg-gray-100 rounded overflow-hidden">
                      <img
                        src={asset.cleanedPath || asset.originalPath}
                        alt={asset.name}
                        className="w-full h-full object-contain"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 pt-4">
              <input
                type="checkbox"
                id="isAlcohol"
                checked={isAlcohol}
                onChange={(e) => setIsAlcohol(e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="isAlcohol" className="text-sm text-gray-700">
                This is an alcohol product (requires Drinkaware)
              </label>
            </div>
          </div>
        );

      case 'style':
        return (
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(LAYOUT_PRESETS).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => setSelectedPreset(key as LayoutPresetKey)}
                className={clsx(
                  'p-4 border rounded-lg text-left transition-all',
                  selectedPreset === key
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <h4 className="font-medium text-gray-900">{preset.name}</h4>
                <p className="text-sm text-gray-500 mt-1">{preset.description}</p>
              </button>
            ))}
          </div>
        );

      case 'content':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Headline *
              </label>
              <input
                type="text"
                value={headline}
                onChange={(e) => setHeadline(e.target.value)}
                placeholder="Enter your main message"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                maxLength={50}
              />
              <p className="text-xs text-gray-500 mt-1">{headline.length}/50 characters</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subheadline (optional)
              </label>
              <input
                type="text"
                value={subhead}
                onChange={(e) => setSubhead(e.target.value)}
                placeholder="Additional supporting text"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                maxLength={100}
              />
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <h5 className="text-sm font-medium text-yellow-800">Content Guidelines</h5>
              <ul className="text-xs text-yellow-700 mt-1 list-disc list-inside">
                <li>No price or discount mentions</li>
                <li>No competition or giveaway wording</li>
                <li>No sustainability claims without approval</li>
                <li>No unsubstantiated claims (#1, best, etc.)</li>
              </ul>
            </div>
          </div>
        );

      case 'customize':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Background Color
              </label>
              <div className="flex gap-2">
                {['#FFFFFF', '#F3F4F6', '#000000', '#1F2937', '#DC2626', '#059669'].map(color => (
                  <button
                    key={color}
                    onClick={() => setSelectedColors([color, selectedColors[1]])}
                    className={clsx(
                      'w-10 h-10 rounded-lg border-2 transition-all',
                      selectedColors[0] === color ? 'border-primary-500 ring-2 ring-primary-300' : 'border-gray-300'
                    )}
                    style={{ backgroundColor: color }}
                  />
                ))}
                <input
                  type="color"
                  value={selectedColors[0]}
                  onChange={(e) => setSelectedColors([e.target.value, selectedColors[1]])}
                  className="w-10 h-10 rounded-lg cursor-pointer"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Text Color
              </label>
              <div className="flex gap-2">
                {['#000000', '#FFFFFF', '#1F2937', '#374151'].map(color => (
                  <button
                    key={color}
                    onClick={() => setSelectedColors([selectedColors[0], color])}
                    className={clsx(
                      'w-10 h-10 rounded-lg border-2 transition-all',
                      selectedColors[1] === color ? 'border-primary-500 ring-2 ring-primary-300' : 'border-gray-300'
                    )}
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Target Format: {canvasSize}
              </label>
              <p className="text-xs text-gray-500">
                Change format in the toolbar. Your design will automatically adapt to other formats on export.
              </p>
            </div>
          </div>
        );

      case 'review':
        return (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-2">Summary</h4>
              <dl className="text-sm space-y-1">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Layout:</dt>
                  <dd className="text-gray-900">{selectedPreset ? LAYOUT_PRESETS[selectedPreset].name : 'None'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Products:</dt>
                  <dd className="text-gray-900">{packshots.length}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Headline:</dt>
                  <dd className="text-gray-900 truncate max-w-[200px]">{headline || 'None'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Alcohol Product:</dt>
                  <dd className="text-gray-900">{isAlcohol ? 'Yes (Drinkaware included)' : 'No'}</dd>
                </div>
              </dl>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <h5 className="text-sm font-medium text-green-800">✓ Ready to Generate</h5>
              <p className="text-xs text-green-700 mt-1">
                Click "Create Design" to generate your creative. You can then fine-tune it in the editor.
              </p>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Design Wizard</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Progress */}
          <div className="flex items-center mt-4">
            {WIZARD_STEPS.map((step, index) => (
              <React.Fragment key={step.id}>
                <div className="flex items-center">
                  <div
                    className={clsx(
                      'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                      index < currentStep
                        ? 'bg-primary-600 text-white'
                        : index === currentStep
                        ? 'bg-primary-100 text-primary-600 border-2 border-primary-600'
                        : 'bg-gray-100 text-gray-400'
                    )}
                  >
                    {index < currentStep ? '✓' : index + 1}
                  </div>
                  <span
                    className={clsx(
                      'ml-2 text-sm hidden sm:block',
                      index === currentStep ? 'text-primary-600 font-medium' : 'text-gray-500'
                    )}
                  >
                    {step.title}
                  </span>
                </div>
                {index < WIZARD_STEPS.length - 1 && (
                  <div
                    className={clsx(
                      'flex-1 h-0.5 mx-2',
                      index < currentStep ? 'bg-primary-600' : 'bg-gray-200'
                    )}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 200px)' }}>
          <h3 className="text-lg font-medium text-gray-900 mb-1">
            {WIZARD_STEPS[currentStep].title}
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            {WIZARD_STEPS[currentStep].description}
          </p>
          {renderStepContent()}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          <button
            onClick={handleBack}
            disabled={currentStep === 0}
            className={clsx(
              'px-4 py-2 text-sm font-medium rounded-lg',
              currentStep === 0
                ? 'text-gray-300 cursor-not-allowed'
                : 'text-gray-700 hover:bg-gray-100'
            )}
          >
            Back
          </button>
          
          {currentStep < WIZARD_STEPS.length - 1 ? (
            <button
              onClick={handleNext}
              disabled={
                (currentStep === 0 && packshots.length === 0) ||
                (currentStep === 1 && !selectedPreset)
              }
              className={clsx(
                'px-4 py-2 text-sm font-medium rounded-lg',
                (currentStep === 0 && packshots.length === 0) || (currentStep === 1 && !selectedPreset)
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-primary-600 text-white hover:bg-primary-700'
              )}
            >
              Next
            </button>
          ) : (
            <button
              onClick={handleComplete}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-primary-600 text-white hover:bg-primary-700"
            >
              Create Design
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default DesignWizard;
