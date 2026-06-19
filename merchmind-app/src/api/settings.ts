import { apiClient, isMock } from './client';
import { mockSettings } from './mock/data';
import type { AppSettings, ApiEnvelope } from '../types/api';

export async function getSettings(): Promise<AppSettings> {
  if (isMock) return mockSettings;
  const { data } = await apiClient.get<ApiEnvelope<AppSettings>>('/settings');
  return data.data;
}

export async function updateSettings(updates: Partial<AppSettings>): Promise<AppSettings> {
  if (isMock) return { ...mockSettings, ...updates };
  const { data } = await apiClient.patch<ApiEnvelope<AppSettings>>('/settings', updates);
  return data.data;
}
