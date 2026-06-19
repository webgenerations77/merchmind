import { apiClient, isMock } from './client';
import { mockSales, mockSalesAnalytics } from './mock/data';
import type { Sale, SalesAnalytics, ApiEnvelope } from '../types/api';

export async function listSales(params?: {
  product_id?: string;
  from_date?: string;
  to_date?: string;
  limit?: number;
}): Promise<Sale[]> {
  if (isMock) {
    if (params?.product_id) return mockSales.filter(s => s.product_id === params.product_id);
    return mockSales;
  }
  const { data } = await apiClient.get<ApiEnvelope<Sale[]>>('/sales', { params });
  return data.data;
}

export async function getSalesByProduct(productId: string): Promise<Sale[]> {
  if (isMock) return mockSales.filter(s => s.product_id === productId);
  const { data } = await apiClient.get<ApiEnvelope<Sale[]>>(`/sales/by-product/${productId}`);
  return data.data;
}

export async function getSalesAnalytics(): Promise<SalesAnalytics> {
  if (isMock) return mockSalesAnalytics;
  const { data } = await apiClient.get<ApiEnvelope<SalesAnalytics>>('/sales/analytics');
  return data.data;
}
