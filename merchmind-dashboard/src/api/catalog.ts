import apiClient from './client';
import type { ApiResponse, CatalogColor } from '../types/api';

export async function getColors(blueprintId: number, providerId: number): Promise<CatalogColor[]> {
  const { data } = await apiClient.get<ApiResponse<CatalogColor[]>>('/catalog/colors', {
    params: { blueprint_id: blueprintId, provider_id: providerId },
  });
  return data.data;
}
