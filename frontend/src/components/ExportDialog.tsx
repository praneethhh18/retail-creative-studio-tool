/**
 * Export Dialog Component
 * Allows selecting channels and downloading exported creatives
 */
import React, { useState } from 'react';
import clsx from 'clsx';
import { useStore } from '../store';
import { exportBatch } from '../api';
import { ExportedFile } from '../types';

interface ExportJob {
  files: ExportedFile[];
}

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

const CHANNELS = [
  { id: 'facebook_feed', label: 'Facebook Feed', size: '1200×628' },
  { id: 'instagram_feed', label: 'Instagram Feed', size: '1080×1080' },
  { id: 'instagram_story', label: 'Instagram Story', size: '1080×1920' },
  { id: 'instore_a4', label: 'In-Store A4', size: '2480×3508' },
] as const;

const FORMATS = ['jpeg', 'png'] as const;

export const ExportDialog: React.FC<ExportDialogProps> = ({ isOpen, onClose }) => {
  const { layout, assets, setIsLoading } = useStore();
  const [selectedChannels, setSelectedChannels] = useState<string[]>(['facebook_feed']);
  const [selectedFormat, setSelectedFormat] = useState<typeof FORMATS[number]>('jpeg');
  const [exportJob, setExportJob] = useState<ExportJob | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleChannel = (channelId: string) => {
    setSelectedChannels((prev) =>
      prev.includes(channelId)
        ? prev.filter((id) => id !== channelId)
        : [...prev, channelId]
    );
  };

  const handleExport = async () => {
    if (!layout || selectedChannels.length === 0) return;

    setIsExporting(true);
    setIsLoading(true);
    setError(null);

    try {
      // Build comprehensive assets map
      // The renderer may look up assets by various keys, so we map multiple ways
      const assetsMap: Record<string, string> = {};
      
      // First, map all uploaded assets
      assets.forEach((asset) => {
        const path = asset.cleanedPath || asset.originalPath;
        
        // Map by ID
        assetsMap[asset.id] = path;
        // Map by the full path 
        assetsMap[path] = path;
        // Map by path without /assets/ prefix
        if (path.startsWith('/assets/')) {
          const withoutPrefix = path.replace('/assets/', '');
          assetsMap[withoutPrefix] = path;
        }
        // Map by original path as well
        if (asset.originalPath && asset.originalPath !== path) {
          assetsMap[asset.originalPath] = path;
          if (asset.originalPath.startsWith('/assets/')) {
            assetsMap[asset.originalPath.replace('/assets/', '')] = path;
          }
        }
      });

      // Then, add any assets directly referenced in layout elements
      // This catches any assets that might be referenced differently
      layout.elements.forEach((element) => {
        if (element.asset && !assetsMap[element.asset]) {
          // Store the asset reference as-is (backend will try to resolve)
          assetsMap[element.asset] = element.asset;
          
          // Also add without /assets/ prefix if present
          if (element.asset.startsWith('/assets/')) {
            const withoutPrefix = element.asset.replace('/assets/', '');
            if (!assetsMap[withoutPrefix]) {
              assetsMap[withoutPrefix] = element.asset;
            }
          }
        }
      });

      console.log('ExportDialog assetsMap:', assetsMap);
      console.log('Layout elements:', layout.elements);
      
      const result = await exportBatch(layout, assetsMap, selectedFormat);
      
      console.log('Export result:', result);
      
      // Convert to ExportJob format - map backend response to frontend types
      const files: ExportedFile[] = result.files?.map((f: any) => {
        // Parse dimensions from size (e.g., "1080x1920")
        const sizeParts = (f.size || '1080x1080').split('x');
        const width = parseInt(sizeParts[0]) || 1080;
        const height = parseInt(sizeParts[1]) || 1080;
        
        return {
          channel: f.size || f.channel || 'unknown',  // Use size as channel name
          url: f.url || `/exports/${f.path?.split('/').pop() || 'export'}`,
          width,
          height,
          size_kb: f.file_size_kb || f.size_kb || 0,
        };
      }) || [];
      
      setExportJob({ files });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setIsExporting(false);
      setIsLoading(false);
    }
  };

  const downloadFile = (file: ExportedFile) => {
    const link = document.createElement('a');
    link.href = `/api${file.url}`;
    link.download = file.url.split('/').pop() || 'export';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const downloadAll = () => {
    if (!exportJob) return;
    exportJob.files.forEach((file) => {
      setTimeout(() => downloadFile(file), 100);
    });
  };

  const handleClose = () => {
    setExportJob(null);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
      />

      {/* Dialog */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Export Creative</h2>
          <button
            onClick={handleClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {!exportJob ? (
            <>
              {/* Channel Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Channels
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {CHANNELS.map((channel) => (
                    <button
                      key={channel.id}
                      onClick={() => toggleChannel(channel.id)}
                      className={clsx(
                        'p-3 rounded-lg border-2 text-left transition-colors',
                        selectedChannels.includes(channel.id)
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      )}
                    >
                      <span className="block text-sm font-medium text-gray-900">
                        {channel.label}
                      </span>
                      <span className="block text-xs text-gray-500">{channel.size}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Format Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Format
                </label>
                <div className="flex gap-4">
                  {FORMATS.map((format) => (
                    <label key={format} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="format"
                        value={format}
                        checked={selectedFormat === format}
                        onChange={() => setSelectedFormat(format)}
                        className="w-4 h-4 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm font-medium text-gray-700 uppercase">
                        {format}
                      </span>
                    </label>
                  ))}
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  All exports will be optimized to under 500KB
                </p>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                  {error}
                </div>
              )}
            </>
          ) : (
            /* Export Results */
            <div>
              <div className="flex items-center gap-2 mb-4 text-green-600">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="font-medium">Export Complete!</span>
              </div>

              <div className="space-y-3 mb-4 max-h-80 overflow-y-auto">
                {exportJob.files.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                  >
                    {/* Image preview */}
                    <div className="w-16 h-16 bg-gray-200 rounded overflow-hidden flex-shrink-0">
                      <img 
                        src={`/api${file.url}`}
                        alt={file.channel}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="block text-sm font-medium text-gray-900 capitalize">
                        {file.channel.replace('x', ' × ')}
                      </span>
                      <span className="text-xs text-gray-500">
                        {file.width}×{file.height} • {(file.size_kb || 0).toFixed(1)} KB
                      </span>
                    </div>
                    <button
                      onClick={() => downloadFile(file)}
                      className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors flex-shrink-0"
                      title="Download"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>

              {exportJob.files.length > 1 && (
                <button
                  onClick={downloadAll}
                  className="w-full btn-primary"
                >
                  Download All ({exportJob.files.length} files)
                </button>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {!exportJob && (
          <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3">
            <button onClick={handleClose} className="btn-secondary">
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting || selectedChannels.length === 0 || !layout}
              className={clsx(
                'btn-primary',
                (isExporting || selectedChannels.length === 0 || !layout) &&
                  'opacity-50 cursor-not-allowed'
              )}
            >
              {isExporting ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Exporting...
                </span>
              ) : (
                `Export ${selectedChannels.length} Channel${selectedChannels.length !== 1 ? 's' : ''}`
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExportDialog;
