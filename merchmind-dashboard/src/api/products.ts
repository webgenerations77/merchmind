import apiClient from './client';
import type { ApiResponse, ProductOut } from '../types/api';

export async function listProducts(status?: string): Promise<ProductOut[]> {
  const params = status ? { status } : {};
  const { data } = await apiClient.get<ApiResponse<ProductOut[]>>('/products', { params });
  return data.data;
}

export async function getProduct(id: string): Promise<ProductOut> {
  const { data } = await apiClient.get<ApiResponse<ProductOut>>(`/products/${id}`);
  return data.data;
}

export async function unpublishProduct(id: string): Promise<void> {
  await apiClient.post(`/products/${id}/unpublish`);
}

export async function retryPublish(id: string): Promise<void> {
  await apiClient.post(`/products/${id}/retry-publish`);
}
