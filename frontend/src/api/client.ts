/**
 * API client for communicating with the backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  UploadResponse,
  GenRequest,
  LayoutsResponse,
  ValidateRequest,
  ValidationResult,
  ExportRequest,
  ExportResponse,
  HealthResponse,
  CopyModerationResult,
  ValidationRule,
} from '../types';

// API base URL - uses proxy in development
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 second timeout for LLM calls
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error handler
const handleError = (error: AxiosError): never => {
  if (error.response) {
    const message = (error.response.data as { detail?: string })?.detail || 
      'An error occurred';
    throw new Error(message);
  } else if (error.request) {
    throw new Error('No response from server. Please check your connection.');
  } else {
    throw new Error(error.message);
  }
};

// Health check
export const checkHealth = async (): Promise<HealthResponse> => {
  try {
    const response = await api.get<HealthResponse>('/');
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

// Upload endpoints
export const uploadPackshot = async (
  file: File,
  removeBackground: boolean = true
): Promise<UploadResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('remove_background', String(removeBackground));

    const response = await api.post<UploadResponse>('/upload/packshot', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const uploadLogo = async (
  file: File,
  removeBackground: boolean = true
): Promise<UploadResponse> => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('remove_background', String(removeBackground));

    const response = await api.post<UploadResponse>('/upload/logo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const uploadBackground = async (file: File): Promise<{ path: string; palette: string[]; asset_id: string }> => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload/background', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const deleteAsset = async (assetId: string): Promise<{ deleted: string[] }> => {
  try {
    const response = await api.delete(`/upload/${assetId}`);
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

// Generate endpoints
export const generateLayouts = async (request: GenRequest): Promise<LayoutsResponse> => {
  try {
    const response = await api.post<LayoutsResponse>('/generate/layouts', request);
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const moderateCopy = async (
  headline: string,
  subhead: string = ''
): Promise<CopyModerationResult> => {
  try {
    const response = await api.post<CopyModerationResult>('/generate/moderate-copy', {
      headline,
      subhead,
    });
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const getLLMStatus = async (): Promise<{ 
  available: boolean; 
  provider: string; 
  model: string | null 
}> => {
  try {
    const response = await api.get('/generate/status');
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

// Validate endpoints
export const validateLayout = async (request: Partial<ValidateRequest> & { layout: ValidateRequest['layout'] }): Promise<ValidationResult> => {
  try {
    // Map frontend channel names to API channel names
    type APIChannel = 'facebook' | 'instagram' | 'stories' | 'in_store';
    const channelMap: Record<string, APIChannel> = {
      'facebook_feed': 'facebook',
      'instagram_feed': 'instagram',
      'instagram_story': 'stories',
      'instore_a4': 'in_store',
      'facebook': 'facebook',
      'instagram': 'instagram',
      'stories': 'stories',
      'in_store': 'in_store',
    };
    
    // Fill in defaults for optional fields
    const fullRequest = {
      layout: request.layout,
      canvas_size: request.canvas_size || '1080x1920',
      is_alcohol: request.is_alcohol ?? false,
      channel: channelMap[request.channel || 'stories'] || 'stories',
    };
    const response = await api.post<ValidationResult>('/validate/check', fullRequest);
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const quickCheck = async (
  headline: string,
  subhead: string = '',
  tescoTagText: string = 'Available at Tesco',
  isAlcohol: boolean = false
): Promise<{ ok: boolean; issues: ValidationResult['issues'] }> => {
  try {
    const response = await api.post('/validate/quick-check', null, {
      params: {
        headline,
        subhead,
        tesco_tag_text: tescoTagText,
        is_alcohol: isAlcohol,
      },
    });
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const getValidationRules = async (): Promise<{ rules: ValidationRule[] }> => {
  try {
    const response = await api.get('/validate/rules');
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

// Export endpoints
export const exportImage = async (request: ExportRequest): Promise<ExportResponse> => {
  try {
    const response = await api.post<ExportResponse>('/export/image', request);
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const exportBatch = async (
  layout: ExportRequest['layout'],
  assetsMap: Record<string, string>,
  format: 'jpeg' | 'png' = 'jpeg'
): Promise<ExportResponse> => {
  try {
    const response = await api.post<ExportResponse>('/export/batch', {
      layout,
      assets_map: assetsMap,
      format,
    });
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const exportZip = async (request: ExportRequest): Promise<Blob> => {
  try {
    const response = await api.post('/export/zip', request, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    return handleError(error as AxiosError);
  }
};

export const downloadExport = (filename: string): string => {
  return `${API_BASE_URL}/export/download/${filename}`;
};

// Asset URL helper
export const getAssetUrl = (path: string): string => {
  if (!path) return '';
  if (path.startsWith('http')) {
    return path;
  }
  // Ensure path starts with /assets/
  let cleanPath = path;
  if (!cleanPath.startsWith('/assets/') && !cleanPath.startsWith('assets/')) {
    cleanPath = `/assets/${cleanPath}`;
  }
  if (!cleanPath.startsWith('/')) {
    cleanPath = `/${cleanPath}`;
  }
  return `${API_BASE_URL}${cleanPath}`;
};

export default api;
