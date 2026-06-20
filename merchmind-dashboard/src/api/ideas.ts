import apiClient from './client';
import type { ApiResponse } from '../types/api';

export interface CustomIdea {
  id: string;
  input_text: string;
  status: string;
  design_id: string | null;
  preferences: Record<string, string>;
  created_at: string;
}

export async function listIdeas(): Promise<CustomIdea[]> {
  const { data } = await apiClient.get<ApiResponse<CustomIdea[]>>('/ideas');
  return data.data;
}

export async function createIdea(text: string, preferences?: Record<string, string>, saveOnly?: boolean): Promise<{ id: string; status: string }> {
  const { data } = await apiClient.post<ApiResponse<{ id: string; status: string }>>('/ideas', { text, preferences, save_only: saveOnly });
  return data.data;
}

export async function generateSavedIdea(id: string): Promise<{ id: string; status: string }> {
  const { data } = await apiClient.post<ApiResponse<{ id: string; status: string }>>(`/ideas/${id}/generate`);
  return data.data;
}

export async function deleteIdea(id: string): Promise<void> {
  await apiClient.delete(`/ideas/${id}`);
}
