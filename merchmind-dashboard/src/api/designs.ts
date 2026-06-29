import apiClient from './client';
import type { ApiResponse, DesignQueueItem, DesignOut } from '../types/api';

export async function getReviewQueue(filter: 'active' | 'archived' | 'all' = 'active'): Promise<DesignQueueItem[]> {
  const { data } = await apiClient.get<ApiResponse<DesignQueueItem[]>>('/designs/queue', { params: { filter } });
  return data.data;
}

export async function getFeaturedDesigns(): Promise<DesignQueueItem[]> {
  const { data } = await apiClient.get<ApiResponse<DesignQueueItem[]>>('/designs/featured');
  return data.data;
}

export async function getDesign(id: string): Promise<DesignOut> {
  const { data } = await apiClient.get<ApiResponse<DesignOut>>(`/designs/${id}`);
  return data.data;
}

export interface ApproveResult {
  id: string;
  status: string;
  published: string[];
  removed: string[];
  failed: { type: string; error: string }[];
}

export async function approveDesign(id: string, productTypes?: string[]): Promise<ApproveResult> {
  const params: Record<string, string> = {};
  if (productTypes && productTypes.length > 0) {
    params.product_types = productTypes.join(',');
  }
  const { data } = await apiClient.patch<ApiResponse<ApproveResult>>(`/designs/${id}/approve`, null, { params });
  return data.data;
}

export async function rejectDesign(id: string): Promise<void> {
  await apiClient.patch(`/designs/${id}/reject`);
}

export async function archiveDesign(id: string): Promise<void> {
  await apiClient.patch(`/designs/${id}/archive`);
}

export async function unarchiveDesign(id: string): Promise<void> {
  await apiClient.patch(`/designs/${id}/unarchive`);
}

export async function revisitDesign(id: string): Promise<void> {
  await apiClient.patch(`/designs/${id}/revisit`);
}

export async function delayDesign(id: string, week: string): Promise<void> {
  await apiClient.patch(`/designs/${id}/delay`, { delayed_to_week: week });
}

export async function toggleFeatured(id: string): Promise<{ is_featured: boolean }> {
  const { data } = await apiClient.patch<ApiResponse<{ id: string; is_featured: boolean }>>(`/designs/${id}/feature`);
  return data.data;
}

export async function regenerateDesign(id: string, newPrompt?: string, forceArchetype?: string): Promise<void> {
  await apiClient.post(`/designs/${id}/regenerate`, { new_prompt: newPrompt, force_archetype: forceArchetype });
}

export interface ChatResponse {
  reply: string;
  conversation: { role: 'user' | 'assistant'; content: string }[];
}

export async function sendChatMessage(designId: string, message: string): Promise<ChatResponse> {
  const { data } = await apiClient.post<ApiResponse<ChatResponse>>(`/designs/${designId}/chat`, { message });
  return data.data;
}

export interface SuggestRegenerateResult {
  task_id: string;
  directive: string;
  version: number;
}

export interface SuggestBrief {
  vibe?: string[];
  change_focus?: string;
  audience?: string[];
}

export async function suggestRegenerate(
  designId: string,
  conversation: { role: string; content: string }[],
  brief?: SuggestBrief,
): Promise<SuggestRegenerateResult> {
  const { data } = await apiClient.post<ApiResponse<SuggestRegenerateResult>>(`/designs/${designId}/suggest-regenerate`, { conversation, ...brief });
  return data.data;
}

export async function updateShopifyCopy(id: string, updates: { shopify_title?: string; shopify_description?: string }): Promise<{ shopify_title: string; shopify_description: string }> {
  const { data } = await apiClient.patch<ApiResponse<{ shopify_title: string; shopify_description: string }>>(`/designs/${id}/shopify-copy`, updates);
  return data.data;
}

export async function clearChat(designId: string): Promise<void> {
  await apiClient.delete(`/designs/${designId}/chat`);
}

export interface RetireResult {
  id: string;
  retired: string[];
  failed: { type: string; error: string }[];
}

export async function retireDesign(id: string): Promise<RetireResult> {
  const { data } = await apiClient.post<ApiResponse<RetireResult>>(`/designs/${id}/retire`);
  return data.data;
}
