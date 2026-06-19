import { create } from 'zustand';
import type { DesignQueueItem } from '../types/api';
import { getReviewQueue, approveDesign as apiApprove, rejectDesign as apiReject, delayDesign as apiDelay } from '../api/designs';

type ReviewAction = 'approved' | 'rejected' | 'delayed';

interface ReviewState {
  queue: DesignQueueItem[];
  currentIndex: number;
  sessionActions: Record<string, ReviewAction>;
  isLoading: boolean;
  error: string | null;
  fetchQueue: () => Promise<void>;
  approveDesign: (id: string) => Promise<void>;
  rejectDesign: (id: string) => Promise<void>;
  delayDesign: (id: string, week: string) => Promise<void>;
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
      set({ queue, isLoading: false, currentIndex: 0, sessionActions: {} });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  approveDesign: async (id: string) => {
    set((s) => ({ sessionActions: { ...s.sessionActions, [id]: 'approved' } }));
    try {
      await apiApprove(id);
    } catch {
      set((s) => { const { [id]: _, ...rest } = s.sessionActions; return { sessionActions: rest }; });
    }
  },

  rejectDesign: async (id: string) => {
    set((s) => ({ sessionActions: { ...s.sessionActions, [id]: 'rejected' } }));
    try {
      await apiReject(id);
    } catch {
      set((s) => { const { [id]: _, ...rest } = s.sessionActions; return { sessionActions: rest }; });
    }
  },

  delayDesign: async (id: string, week: string) => {
    set((s) => ({ sessionActions: { ...s.sessionActions, [id]: 'delayed' } }));
    try {
      await apiDelay(id, week);
    } catch {
      set((s) => { const { [id]: _, ...rest } = s.sessionActions; return { sessionActions: rest }; });
    }
  },

  goToNext: () => {
    const { currentIndex, queue } = get();
    if (currentIndex < queue.length - 1) set({ currentIndex: currentIndex + 1 });
  },
  goToPrevious: () => {
    const { currentIndex } = get();
    if (currentIndex > 0) set({ currentIndex: currentIndex - 1 });
  },
  goToIndex: (index: number) => set({ currentIndex: index }),
  reset: () => set({ queue: [], currentIndex: 0, sessionActions: {}, error: null }),
}));
