import { apiClient, isMock } from './client';
import { mockMarketingAssets } from './mock/data';
import type { MarketingAsset, ApiEnvelope } from '../types/api';

export async function getDesignAssets(designId: string): Promise<MarketingAsset[]> {
  if (isMock) return mockMarketingAssets.filter(a => a.design_id === designId);
  const { data } = await apiClient.get<ApiEnvelope<MarketingAsset[]>>(`/marketing/${designId}`);
  return data.data;
}

export async function approveAsset(assetId: string): Promise<void> {
  if (isMock) return;
  await apiClient.patch(`/marketing/${assetId}/approve`);
}

export async function disableAsset(assetId: string): Promise<void> {
  if (isMock) return;
  await apiClient.patch(`/marketing/${assetId}/disable`);
}

export async function updateAssetContent(
  assetId: string,
  updates: Partial<MarketingAsset>,
): Promise<MarketingAsset> {
  if (isMock) return mockMarketingAssets[0];
  const { data } = await apiClient.patch<ApiEnvelope<MarketingAsset>>(`/marketing/${assetId}/content`, updates);
  return data.data;
}
