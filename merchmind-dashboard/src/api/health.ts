import apiClient from './client';
import type { IntegrationHealth } from '../types/api';

export async function getIntegrationHealth(): Promise<IntegrationHealth> {
  const { data } = await apiClient.get<{ ok: boolean; services: IntegrationHealth['services'] }>('/health/integrations');
  return data as unknown as IntegrationHealth;
}

export interface ApiBalanceResult {
  ok: boolean;
  services: Record<string, { service: string; ok: boolean; status?: string; error?: string }>;
}

export async function getApiBalance(): Promise<ApiBalanceResult> {
  const { data } = await apiClient.get<ApiBalanceResult>('/health/api-balance');
  return data;
}
