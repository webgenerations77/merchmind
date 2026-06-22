import apiClient from './client';
import type { ApiResponse } from '../types/api';

export interface UsageSummary {
  period: string;
  total_cost: number;
  total_calls: number;
  by_service: {
    service: string;
    calls: number;
    input_tokens: number;
    output_tokens: number;
    total_cost: number;
  }[];
  by_operation: {
    service: string;
    operation: string;
    model: string;
    calls: number;
    total_cost: number;
  }[];
  daily: {
    day: string;
    service: string;
    cost: number;
    calls: number;
  }[];
}

export async function getUsageSummary(period: string = 'month'): Promise<UsageSummary> {
  const { data } = await apiClient.get<ApiResponse<UsageSummary>>(`/api-usage/summary?period=${period}`);
  return data.data;
}

export interface UsageLogEntry {
  id: string;
  service: string;
  operation: string;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  estimated_cost: number;
  design_id: string | null;
  batch_id: string | null;
  created_at: string;
}

export interface UsageHistoryResult {
  total: number;
  offset: number;
  limit: number;
  logs: UsageLogEntry[];
}

export async function getUsageHistory(
  period: string = 'day',
  service?: string,
  operation?: string,
  limit: number = 200,
  offset: number = 0,
): Promise<UsageHistoryResult> {
  const params = new URLSearchParams({ period, limit: String(limit), offset: String(offset) });
  if (service) params.set('service', service);
  if (operation) params.set('operation', operation);
  const { data } = await apiClient.get<ApiResponse<UsageHistoryResult>>(`/api-usage/history?${params}`);
  return data.data;
}
