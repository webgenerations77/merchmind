import { create } from 'zustand';
import type { DesignQueueItem } from '../types/api';
import { getReviewQueue, approveDesign, rejectDesign, delayDesign } from '../api/designs';

type ReviewAction = 'approved' | 'rejected' | 'delayed';

interface ReviewState {
  queue: DesignQueueItem[];
  currentIndex: number;
  sessionActions: Record<string, ReviewAction>;
  isLoading: boolean;
  error: string | null;

  fetchQueue: () => Promise<void>;
  approveDesign: (designId: string) => Promise<void>;
  rejectDesign: (designId: string) => Promise<void>;
  delayDesign: (designId: string, week: string) => Promise<void>;
  goToNext: () => void;
  goToPrevious: () => void;
  goToIndex: (index: number) => void;
  reset: () => void;
}

export const useReviewStore = create<ReviewState>((set, get) => ({
  queue: [],
  currentIndex: 0,
  sessionActions: {},
  isLoading: false,
  error: null,

  fetchQueue: async () => {
    set({ isLoading: true, error: null });
    try {
      const queue = await getReviewQueue();
      const sorted = [...queue].sort((a, b) => b.final_score - a.final_score);
      set({ queue: sorted, isLoading: false, currentIndex: 0, sessionActions: {} });
    } catch (e: unknown) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  approveDesign: async (designId: string) => {
    set(state => ({
      sessionActions: { ...state.sessionActions, [designId]: 'approved' },
    }));
    try {
      await approveDesign(designId);
    } catch {
      set(state => {
        const { [designId]: _, ...rest } = state.sessionActions;
        return { sessionActions: rest };
      });
      throw new Error('Failed to approve design');
    }
  },

  rejectDesign: async (designId: string) => {
    set(state => ({
      sessionActions: { ...state.sessionActions, [designId]: 'rejected' },
    }));
    try {
      await rejectDesign(designId);
    } catch {
      set(state => {
        const { [designId]: _, ...rest } = state.sessionActions;
        return { sessionActions: rest };
      });
      throw new Error('Failed to reject design');
    }
  },

  delayDesign: async (designId: string, week: string) => {
    set(state => ({
      sessionActions: { ...state.sessionActions, [designId]: 'delayed' },
    }));
    try {
      await delayDesign(designId, week);
    } catch {
      set(state => {
        const { [designId]: _, ...rest } = state.sessionActions;
        return { sessionActions: rest };
      });
      throw new Error('Failed to delay design');
    }
  },

  goToNext: () => {
    const { currentIndex, queue } = get();
    if (currentIndex < queue.length - 1) {
      set({ currentIndex: currentIndex + 1 });
    }
  },

  goToPrevious: () => {
    const { currentIndex } = get();
    if (currentIndex > 0) {
      set({ currentIndex: currentIndex - 1 });
    }
  },

  goToIndex: (index: number) => {
    set({ currentIndex: index });
  },

  reset: () => set({ queue: [], currentIndex: 0, sessionActions: {}, error: null }),
}));
