import apiClient from './client';
import type { ApiResponse, AppSettings, NicheCluster } from '../types/api';

export async function getSettings(): Promise<AppSettings> {
  const { data } = await apiClient.get<ApiResponse<AppSettings>>('/settings');
  return data.data;
}

export async function updateSettings(updates: Partial<AppSettings>): Promise<AppSettings> {
  const { data } = await apiClient.patch<ApiResponse<AppSettings>>('/settings', updates);
  return data.data;
}

export async function listClusters(): Promise<NicheCluster[]> {
  const { data } = await apiClient.get<ApiResponse<NicheCluster[]>>('/niche-clusters');
  return data.data;
}
