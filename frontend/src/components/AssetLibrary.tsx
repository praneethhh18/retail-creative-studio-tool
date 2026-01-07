/**
 * Asset Library Component
 * Displays uploaded packshots, logos, and backgrounds
 */
import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import clsx from 'clsx';
import { useStore } from '../store';
import { Asset, LayoutElement } from '../types';
import { uploadPackshot, uploadLogo, uploadBackground, deleteAsset, getAssetUrl } from '../api';

interface AssetCardProps {
  asset: Asset;
  onDelete: (id: string) => void;
  onAddToCanvas?: (asset: Asset) => void;
}

const AssetCard: React.FC<AssetCardProps> = ({ asset, onDelete, onAddToCanvas }) => {
  const imagePath = asset.cleanedPath || asset.originalPath;

  return (
    <div className="group relative bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div 
        className="aspect-square bg-gray-100 flex items-center justify-center cursor-pointer hover:bg-gray-200 transition-colors"
        onClick={() => onAddToCanvas?.(asset)}
        title="Click to add to canvas"
      >
        <img
          src={getAssetUrl(imagePath)}
          alt={asset.name}
          className="max-w-full max-h-full object-contain"
          crossOrigin="anonymous"
        />
      </div>
      <div className="p-2">
        <p className="text-xs font-medium text-gray-700 truncate">{asset.name}</p>
        <p className="text-xs text-gray-500 capitalize">{asset.type}</p>
        {asset.palette.length > 0 && (
          <div className="flex gap-1 mt-1">
            {asset.palette.slice(0, 3).map((color, i) => (
              <div
                key={i}
                className="w-4 h-4 rounded-full border border-gray-200"
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
        )}
      </div>
      {/* Add to canvas button */}
      <button
        onClick={() => onAddToCanvas?.(asset)}
        className="absolute top-1 left-1 p-1 bg-primary-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
        title="Add to canvas"
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      </button>
      <button
        onClick={() => onDelete(asset.id)}
        className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
        title="Delete asset"
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
};

interface UploadZoneProps {
  type: 'packshot' | 'logo' | 'background';
  onUpload: (asset: Asset) => void;
}

const UploadZone: React.FC<UploadZoneProps> = ({ type, onUpload }) => {
  const { setIsLoading } = useStore();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      setIsLoading(true);
      try {
        for (const file of acceptedFiles) {
          let response;
          
          if (type === 'packshot') {
            response = await uploadPackshot(file, true);
          } else if (type === 'logo') {
            response = await uploadLogo(file, true);
          } else {
            const bgResponse = await uploadBackground(file);
            response = {
              original: bgResponse.path,
              cleaned: bgResponse.path,
              palette: bgResponse.palette,
              asset_id: bgResponse.asset_id,
            };
          }

          const asset: Asset = {
            id: response.asset_id,
            type,
            originalPath: response.original,
            cleanedPath: response.cleaned,
            palette: response.palette,
            name: file.name,
          };

          onUpload(asset);
        }
      } catch (error) {
        console.error('Upload failed:', error);
        alert('Upload failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
      } finally {
        setIsLoading(false);
      }
    },
    [type, onUpload, setIsLoading]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const labels = {
    packshot: 'Packshot',
    logo: 'Logo',
    background: 'Background',
  };

  return (
    <div
      {...getRootProps()}
      className={clsx('dropzone text-center', isDragActive && 'active')}
    >
      <input {...getInputProps()} />
      <svg
        className="mx-auto h-8 w-8 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
        />
      </svg>
      <p className="mt-2 text-sm text-gray-600">
        Drop {labels[type]} here or <span className="text-primary-600">browse</span>
      </p>
      <p className="text-xs text-gray-400 mt-1">PNG, JPG up to 10MB</p>
    </div>
  );
};

export const AssetLibrary: React.FC = () => {
  const { assets, addAsset, removeAsset, setIsLoading, layout, setLayout, addElement } = useStore();

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this asset?')) return;

    setIsLoading(true);
    try {
      await deleteAsset(id);
      removeAsset(id);
    } catch (error) {
      console.error('Delete failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Add an asset to the current canvas
  const handleAddToCanvas = useCallback((asset: Asset) => {
    const assetPath = asset.cleanedPath || asset.originalPath;
    console.log('Adding asset to canvas:', { type: asset.type, assetPath, layout: layout?.id });
    
    // For backgrounds, update the background element or add background image
    if (asset.type === 'background') {
      if (!layout) {
        // Create new layout with background image
        const newLayout = {
          id: `manual-${Date.now()}`,
          score: 1.0,
          elements: [
            { type: 'background' as const, color: '#FFFFFF' },
            { type: 'packshot' as const, asset: assetPath, x: 0, y: 0, width: 100, height: 100, z: 0 },
          ],
        };
        setLayout(newLayout);
      } else {
        // Add background image to existing layout at the bottom layer
        const newElement: LayoutElement = {
          type: 'packshot',
          asset: assetPath,
          x: 0,
          y: 0,
          width: 100,
          height: 100,
          z: 0, // Bottom layer
        };
        addElement(newElement);
      }
      return;
    }
    
    // Create a new element based on asset type (logo or packshot)
    const newElement: LayoutElement = {
      type: asset.type === 'logo' ? 'logo' : 'packshot',
      asset: assetPath,
      x: 25 + Math.random() * 10,  // Slightly randomize position
      y: 25 + Math.random() * 10,
      width: asset.type === 'logo' ? 25 : 40,
      height: asset.type === 'logo' ? 20 : 40,
      z: 10,  // Put on top
    };
    
    console.log('Creating element:', newElement);

    // If no layout exists, create one with just the background and this asset
    if (!layout) {
      const newLayout = {
        id: `manual-${Date.now()}`,
        score: 1.0,
        elements: [
          { type: 'background' as const, color: '#FFFFFF' },
          newElement,
        ],
      };
      console.log('Creating new layout with element:', newLayout);
      setLayout(newLayout);
    } else {
      // Add to existing layout
      console.log('Adding to existing layout:', layout.id);
      addElement(newElement);
    }
  }, [layout, setLayout, addElement]);

  const packshots = assets.filter((a) => a.type === 'packshot');
  const logos = assets.filter((a) => a.type === 'logo');
  const backgrounds = assets.filter((a) => a.type === 'background');

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header">Asset Library</div>
      <div className="panel-body flex-1 overflow-y-auto space-y-4">
        {/* Packshots */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Packshots
            <span className="text-xs font-normal text-gray-400 ml-2">Click to add</span>
          </h4>
          {packshots.length > 0 && (
            <div className="grid grid-cols-2 gap-2 mb-2">
              {packshots.map((asset) => (
                <AssetCard 
                  key={asset.id} 
                  asset={asset} 
                  onDelete={handleDelete}
                  onAddToCanvas={handleAddToCanvas}
                />
              ))}
            </div>
          )}
          <UploadZone type="packshot" onUpload={addAsset} />
        </div>

        {/* Logos */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Logos
            <span className="text-xs font-normal text-gray-400 ml-2">Click to add</span>
          </h4>
          {logos.length > 0 && (
            <div className="grid grid-cols-2 gap-2 mb-2">
              {logos.map((asset) => (
                <AssetCard 
                  key={asset.id} 
                  asset={asset} 
                  onDelete={handleDelete}
                  onAddToCanvas={handleAddToCanvas}
                />
              ))}
            </div>
          )}
          <UploadZone type="logo" onUpload={addAsset} />
        </div>

        {/* Backgrounds */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Backgrounds</h4>
          {backgrounds.length > 0 && (
            <div className="grid grid-cols-2 gap-2 mb-2">
              {backgrounds.map((asset) => (
                <AssetCard key={asset.id} asset={asset} onDelete={handleDelete} />
              ))}
            </div>
          )}
          <UploadZone type="background" onUpload={addAsset} />
        </div>
      </div>
    </div>
  );
};

export default AssetLibrary;
