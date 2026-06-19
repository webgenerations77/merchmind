import { apiClient, isMock } from './client';
import { mockProducts } from './mock/data';
import type { Product, ApiEnvelope } from '../types/api';

export async function listProducts(status?: string): Promise<Product[]> {
  if (isMock) return mockProducts;
  const params = status ? { status } : {};
  const { data } = await apiClient.get<ApiEnvelope<Product[]>>('/products', { params });
  return data.data;
}

export async function getProduct(productId: string): Promise<Product> {
  if (isMock) {
    const p = mockProducts.find(p => p.id === productId);
    if (!p) throw new Error('Product not found');
    return p;
  }
  const { data } = await apiClient.get<ApiEnvelope<Product>>(`/products/${productId}`);
  return data.data;
}

export async function updateProduct(
  productId: string,
  updates: { retail_price?: number; publish_status?: string },
): Promise<Product> {
  if (isMock) return mockProducts[0];
  const { data } = await apiClient.patch<ApiEnvelope<Product>>(`/products/${productId}`, updates);
  return data.data;
}

export async function unpublishProduct(productId: string): Promise<void> {
  if (isMock) return;
  await apiClient.post(`/products/${productId}/unpublish`);
}
