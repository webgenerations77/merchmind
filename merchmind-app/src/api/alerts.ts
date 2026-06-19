import { apiClient, isMock } from './client';
import { mockAlerts } from './mock/data';
import type { Alert, ApiEnvelope } from '../types/api';

export async function listAlerts(params?: { resolved?: boolean; severity?: string }): Promise<Alert[]> {
  if (isMock) {
    if (params?.resolved !== undefined) return mockAlerts.filter(a => a.resolved === params.resolved);
    return mockAlerts;
  }
  const { data } = await apiClient.get<ApiEnvelope<Alert[]>>('/alerts', { params });
  return data.data;
}

export async function resolveAlert(alertId: string): Promise<void> {
  if (isMock) return;
  await apiClient.patch(`/alerts/${alertId}/resolve`);
}
