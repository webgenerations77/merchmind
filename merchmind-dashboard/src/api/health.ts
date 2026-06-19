import apiClient from './client';
import type { IntegrationHealth } from '../types/api';

export async function getIntegrationHealth(): Promise<IntegrationHealth> {
  const { data } = await apiClient.get<{ ok: boolean; services: IntegrationHealth['services'] }>('/health/integrations');
  return data as unknown as IntegrationHealth;
}
