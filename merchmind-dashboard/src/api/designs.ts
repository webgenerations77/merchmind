import apiClient from './client';
import type { ApiResponse, DesignQueueItem, DesignOut } from '../types/api';

export async function getReviewQueue(): Promise<DesignQueueItem[]> {
  const { data } = await apiClient.get<ApiResponse<DesignQueueItem[]>>('/designs/queue');
  return data.data;
}

export async function getDesign(id: string): Promise<DesignOut> {
  const { data } = await apiClient.get<ApiResponse<DesignOut>>(`/designs/${id}`);
  return data.data;
}

export async function approveDesign(id: string, productTypes?: string[]): Promise<void> {
  const params: Record<string, string> = {};
  if (productTypes && productTypes.length > 0) {
    params.product_types = productTypes.join(',');
  }
  await apiClient.patch(`/designs/${id}/approve`, null, { params });
}

export async function rejectDesign(id: string): Promise<void> {
  await apiClient.patch(`/designs/${id}/reject`);
}

export async function delayDesign(id: string, week: string): Promise<void> {
  await apiClient.patch(`/designs/${id}/delay`, { delayed_to_week: week });
}

export async function regenerateDesign(id: string, newPrompt?: string, forceArchetype?: string): Promise<void> {
  await apiClient.post(`/designs/${id}/regenerate`, { new_prompt: newPrompt, force_archetype: forceArchetype });
}
