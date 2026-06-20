import apiClient from './client';
import type { ApiResponse } from '../types/api';

export interface MarketingAsset {
  id: string;
  design_id: string;
  channel: string;
  content: Record<string, string>;
  status: string;
  scheduled_for: string | null;
  posted_at: string | null;
  post_url: string | null;
  created_at: string;
  design_name?: string;
  design_image?: string;
}

export async function listMarketingAssets(): Promise<MarketingAsset[]> {
  const { data } = await apiClient.get<ApiResponse<MarketingAsset[]>>('/marketing');
  return data.data;
}

export async function getDesignAssets(designId: string): Promise<MarketingAsset[]> {
  const { data } = await apiClient.get<ApiResponse<MarketingAsset[]>>(`/marketing/${designId}`);
  return data.data;
}
