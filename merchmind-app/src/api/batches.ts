import { apiClient, isMock } from './client';
import { mockBatches } from './mock/data';
import type { Batch, ApiEnvelope } from '../types/api';

export async function listBatches(): Promise<Batch[]> {
  if (isMock) return mockBatches;
  const { data } = await apiClient.get<ApiEnvelope<Batch[]>>('/batches');
  return data.data;
}

export async function getCurrentBatch(): Promise<Batch | null> {
  if (isMock) return mockBatches[0] ?? null;
  const { data } = await apiClient.get<ApiEnvelope<Batch | null>>('/batches/current');
  return data.data;
}

export async function getBatch(batchId: string): Promise<Batch> {
  if (isMock) return mockBatches[0];
  const { data } = await apiClient.get<ApiEnvelope<Batch>>(`/batches/${batchId}`);
  return data.data;
}

export async function triggerBatch(): Promise<{ task_id: string; message: string }> {
  if (isMock) return { task_id: 'mock-task-id', message: 'Mock batch triggered' };
  const { data } = await apiClient.post<ApiEnvelope<{ task_id: string; message: string }>>('/batches/trigger');
  return data.data;
}
