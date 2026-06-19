import apiClient from './client';
import type { ApiResponse, AlertOut } from '../types/api';

export async function listAlerts(resolved?: boolean): Promise<AlertOut[]> {
  const params: Record<string, unknown> = {};
  if (resolved !== undefined) params.resolved = resolved;
  const { data } = await apiClient.get<ApiResponse<AlertOut[]>>('/alerts', { params });
  return data.data;
}

export async function resolveAlert(id: string): Promise<void> {
  await apiClient.patch(`/alerts/${id}/resolve`);
}
