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

export async function createIdea(text: string, preferences?: Record<string, string>): Promise<{ id: string; status: string; design_id: string | null }> {
  const { data } = await apiClient.post<ApiResponse<{ id: string; status: string; design_id: string | null }>>('/ideas', { text, preferences });
  return data.data;
}
