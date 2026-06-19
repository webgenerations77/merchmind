import { create } from 'zustand';
import type { Batch } from '../types/api';
import { getCurrentBatch, triggerBatch } from '../api/batches';

interface BatchState {
  currentBatch: Batch | null;
  isLoading: boolean;
  error: string | null;
  fetchCurrentBatch: () => Promise<void>;
  triggerBatch: () => Promise<Batch>;
}

export const useBatchStore = create<BatchState>((set) => ({
  currentBatch: null,
  isLoading: false,
  error: null,

  fetchCurrentBatch: async () => {
    set({ isLoading: true, error: null });
    try {
      const batch = await getCurrentBatch();
      set({ currentBatch: batch, isLoading: false });
    } catch (e: unknown) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  triggerBatch: async () => {
    const result = await triggerBatch();
    const batch: Batch = {
      id: result.task_id,
      status: 'running',
      started_at: new Date().toISOString(),
      completed_at: null,
      created_at: new Date().toISOString(),
      total_designs: 0,
      approved_designs: 0,
      rejected_designs: 0,
      error_message: null,
    };
    set({ currentBatch: batch });
    return batch;
  },
}));
