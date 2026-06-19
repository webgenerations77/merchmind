import { apiClient, isMock } from './client';
import { mockDesigns } from './mock/data';
import type { Design, DesignQueueItem, ApiEnvelope } from '../types/api';

export async function getReviewQueue(): Promise<DesignQueueItem[]> {
  if (isMock) return mockDesigns as DesignQueueItem[];
  const { data } = await apiClient.get<ApiEnvelope<DesignQueueItem[]>>('/designs/queue');
  return data.data;
}

export async function getDesign(designId: string): Promise<Design> {
  if (isMock) {
    const d = mockDesigns.find(d => d.id === designId);
    if (!d) throw new Error('Design not found');
    return d as Design;
  }
  const { data } = await apiClient.get<ApiEnvelope<Design>>(`/designs/${designId}`);
  return data.data;
}

export async function approveDesign(designId: string): Promise<void> {
  if (isMock) return;
  await apiClient.patch(`/designs/${designId}/approve`);
}

export async function rejectDesign(designId: string): Promise<void> {
  if (isMock) return;
  await apiClient.patch(`/designs/${designId}/reject`);
}

export async function delayDesign(designId: string, delayedToWeek: string): Promise<void> {
  if (isMock) return;
  await apiClient.patch(`/designs/${designId}/delay`, { delayed_to_week: delayedToWeek });
}

export async function regenerateDesign(
  designId: string,
  newPrompt: string,
  forceArchetype?: string,
): Promise<{ task_id: string }> {
  if (isMock) return { task_id: 'mock-regen-task' };
  const { data } = await apiClient.post<ApiEnvelope<{ task_id: string }>>(`/designs/${designId}/regenerate`, {
    new_prompt: newPrompt,
    force_archetype: forceArchetype ?? null,
  });
  return data.data;
}

export async function getDesignVersions(designId: string): Promise<Design[]> {
  if (isMock) return mockDesigns.filter(d => d.id === designId) as Design[];
  const { data } = await apiClient.get<ApiEnvelope<Design[]>>(`/designs/${designId}/versions`);
  return data.data;
}
