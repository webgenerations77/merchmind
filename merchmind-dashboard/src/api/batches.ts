import apiClient from './client';
import type { ApiResponse, BatchOut, BatchDetailOut } from '../types/api';

export async function listBatches(): Promise<BatchOut[]> {
  const { data } = await apiClient.get<ApiResponse<BatchOut[]>>('/batches');
  return data.data;
}

export async function getBatch(id: string): Promise<BatchOut> {
  const { data } = await apiClient.get<ApiResponse<BatchOut>>(`/batches/${id}`);
  return data.data;
}

export async function getBatchDetail(id: string): Promise<BatchDetailOut> {
  const { data } = await apiClient.get<ApiResponse<BatchDetailOut>>(`/batches/${id}/detail`);
  return data.data;
}

export async function getCurrentBatch(): Promise<BatchOut | null> {
  const { data } = await apiClient.get<ApiResponse<BatchOut | null>>('/batches/current');
  return data.data;
}

export interface BatchConfig {
  num_designs?: number;
  trend_sources?: string[];
  style_filter?: string;
  product_focus?: string[];
}

export async function triggerBatch(config?: BatchConfig): Promise<{ task_id: string; message: string }> {
  const { data } = await apiClient.post<ApiResponse<{ task_id: string; message: string }>>('/batches/trigger', config || {});
  return data.data;
}

export async function retryFailedItems(batchId: string): Promise<{ retried: number; total_failed: number; message: string }> {
  const { data } = await apiClient.post<ApiResponse<{ retried: number; total_failed: number; message: string }>>(`/batches/${batchId}/retry-failed`);
  return data.data;
}

export function getExportUrl(batchId: string): string {
  return `${apiClient.defaults.baseURL}/batches/${batchId}/export`;
}
