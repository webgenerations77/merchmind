import apiClient from './client';
import type { ApiResponse, ProductOut } from '../types/api';

export async function listProducts(status?: string, includeRetired?: boolean, search?: string): Promise<ProductOut[]> {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  if (includeRetired) params.include_retired = 'true';
  if (search) params.search = search;
  const { data } = await apiClient.get<ApiResponse<ProductOut[]>>('/products', { params });
  return data.data;
}

export async function getProduct(id: string): Promise<ProductOut> {
  const { data } = await apiClient.get<ApiResponse<ProductOut>>(`/products/${id}`);
  return data.data;
}

export async function updateProduct(id: string, updates: { retail_price?: number; publish_status?: string }): Promise<ProductOut> {
  const { data } = await apiClient.patch<ApiResponse<ProductOut>>(`/products/${id}`, updates);
  return data.data;
}

export async function unpublishProduct(id: string): Promise<void> {
  await apiClient.post(`/products/${id}/unpublish`);
}

export async function retryPublish(id: string): Promise<void> {
  await apiClient.post(`/products/${id}/retry-publish`);
}
