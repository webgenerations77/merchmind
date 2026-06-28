import apiClient from './client';
import type { ApiResponse } from '../types/api';

export interface TrendOut {
  id: string;
  batch_id: string;
  source: string;
  raw_signal: string;
  source_url: string | null;
  source_metadata: Record<string, unknown>;
  trend_score: number;
  viability_score: number;
  final_score: number;
  claude_reasoning: string | null;
  risk_flag: string;
  risk_reason: string | null;
  status: string;
  approval_status: 'pending_review' | 'approved' | 'rejected';
  selected_generator: string | null;
  proposed_archetype: string | null;
  created_at: string;
}

export interface BatchTrendsResult {
  trends: TrendOut[];
  batch_status: string;
  generator_costs: Record<string, number>;
}

export async function getBatchTrends(batchId: string): Promise<BatchTrendsResult> {
  const { data } = await apiClient.get<ApiResponse<BatchTrendsResult>>(
    `/trends/batch/${batchId}`
  );
  return data.data;
}

export async function approveTrend(
  trendId: string,
  selectedGenerator?: string
): Promise<TrendOut> {
  const { data } = await apiClient.patch<ApiResponse<TrendOut>>(
    `/trends/${trendId}/approve`,
    { selected_generator: selectedGenerator ?? null }
  );
  return data.data;
}

export async function rejectTrend(trendId: string): Promise<TrendOut> {
  const { data } = await apiClient.patch<ApiResponse<TrendOut>>(
    `/trends/${trendId}/reject`
  );
  return data.data;
}

export async function setTrendGenerator(
  trendId: string,
  selectedGenerator: string
): Promise<TrendOut> {
  const { data } = await apiClient.patch<ApiResponse<TrendOut>>(
    `/trends/${trendId}/generator`,
    { selected_generator: selectedGenerator }
  );
  return data.data;
}

export async function bulkTrendAction(
  trendIds: string[],
  action: 'approve' | 'reject',
  selectedGenerator?: string
): Promise<{ updated: number; action: string }> {
  const { data } = await apiClient.post<ApiResponse<{ updated: number; action: string }>>(
    `/trends/bulk-action`,
    { trend_ids: trendIds, action, selected_generator: selectedGenerator ?? null }
  );
  return data.data;
}

export async function generateApproved(batchId: string): Promise<{ task_id: string; message: string }> {
  const { data } = await apiClient.post<ApiResponse<{ task_id: string; message: string }>>(
    `/batches/${batchId}/generate-approved`
  );
  return data.data;
}
