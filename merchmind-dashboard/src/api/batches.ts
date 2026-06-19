import apiClient from './client';
import type { ApiResponse, BatchOut } from '../types/api';

export async function listBatches(): Promise<BatchOut[]> {
  const { data } = await apiClient.get<ApiResponse<BatchOut[]>>('/batches');
  return data.data;
}

export async function getBatch(id: string): Promise<BatchOut> {
  const { data } = await apiClient.get<ApiResponse<BatchOut>>(`/batches/${id}`);
  return data.data;
}

export async function getCurrentBatch(): Promise<BatchOut | null> {
  const { data } = await apiClient.get<ApiResponse<BatchOut | null>>('/batches/current');
  return data.data;
}

export async function triggerBatch(): Promise<{ task_id: string; message: string }> {
  const { data } = await apiClient.post<ApiResponse<{ task_id: string; message: string }>>('/batches/trigger');
  return data.data;
}
