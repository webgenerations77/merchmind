import apiClient from './client';
import type { ApiResponse, CollectionOut } from '../types/api';

export async function listCollections(): Promise<CollectionOut[]> {
  const { data } = await apiClient.get<ApiResponse<CollectionOut[]>>('/collections');
  return data.data;
}

export async function getCollection(id: string): Promise<CollectionOut> {
  const { data } = await apiClient.get<ApiResponse<CollectionOut>>(`/collections/${id}`);
  return data.data;
}

export async function createCollection(body: {
  name: string;
  description?: string;
  style_guide?: Record<string, unknown>;
  max_designs?: number;
}): Promise<CollectionOut> {
  const { data } = await apiClient.post<ApiResponse<CollectionOut>>('/collections', body);
  return data.data;
}

export async function updateCollection(id: string, body: Partial<CollectionOut>): Promise<CollectionOut> {
  const { data } = await apiClient.patch<ApiResponse<CollectionOut>>(`/collections/${id}`, body);
  return data.data;
}

export async function deleteCollection(id: string): Promise<void> {
  await apiClient.delete(`/collections/${id}`);
}

export async function generateCollectionDesigns(id: string): Promise<{ generating: number }> {
  const { data } = await apiClient.post<ApiResponse<{ generating: number }>>(`/collections/${id}/generate`);
  return data.data;
}
