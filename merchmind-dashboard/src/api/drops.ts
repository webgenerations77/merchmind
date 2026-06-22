import apiClient from './client';
import type { ApiResponse, MerchDropOut, MerchDropDetail } from '../types/api';

export async function listDrops(): Promise<MerchDropOut[]> {
  const { data } = await apiClient.get<ApiResponse<MerchDropOut[]>>('/drops');
  return data.data;
}

export async function listUpcomingDrops(): Promise<MerchDropOut[]> {
  const { data } = await apiClient.get<ApiResponse<MerchDropOut[]>>('/drops/upcoming');
  return data.data;
}

export async function getDrop(id: string): Promise<MerchDropDetail> {
  const { data } = await apiClient.get<ApiResponse<MerchDropDetail>>(`/drops/${id}`);
  return data.data;
}

export async function createDrop(body: { name: string; scheduled_at: string }): Promise<MerchDropOut> {
  const { data } = await apiClient.post<ApiResponse<MerchDropOut>>('/drops', body);
  return data.data;
}

export async function updateDrop(id: string, body: { name?: string; scheduled_at?: string }): Promise<MerchDropOut> {
  const { data } = await apiClient.patch<ApiResponse<MerchDropOut>>(`/drops/${id}`, body);
  return data.data;
}

export async function deleteDrop(id: string): Promise<void> {
  await apiClient.delete(`/drops/${id}`);
}

export async function publishDropNow(id: string): Promise<{ id: string; status: string }> {
  const { data } = await apiClient.post<ApiResponse<{ id: string; status: string }>>(`/drops/${id}/publish`);
  return data.data;
}

export async function removeProductFromDrop(dropId: string, productId: string): Promise<void> {
  await apiClient.post(`/drops/${dropId}/remove-product/${productId}`);
}

export interface ScheduleDesignResult {
  design_id: string;
  drop_id: string;
  drop_name: string;
  status: string;
  published_to_printify: string[];
  failed: { type: string; error: string }[];
}

export async function scheduleDesignForDrop(
  designId: string,
  params: { drop_id?: string; drop_name?: string; scheduled_at?: string },
): Promise<ScheduleDesignResult> {
  const { data } = await apiClient.post<ApiResponse<ScheduleDesignResult>>(
    `/drops/schedule-design/${designId}`,
    null,
    { params },
  );
  return data.data;
}
