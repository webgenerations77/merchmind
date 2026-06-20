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
