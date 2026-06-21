import { create } from 'zustand';
import type { DesignQueueItem } from '../types/api';
import {
  getReviewQueue,
  approveDesign as apiApprove,
  rejectDesign as apiReject,
  archiveDesign as apiArchive,
  unarchiveDesign as apiUnarchive,
  revisitDesign as apiRevisit,
  delayDesign as apiDelay,
} from '../api/designs';

type ReviewAction = 'approved' | 'rejected' | 'archived' | 'revisited' | 'delayed';

interface ReviewState {
  queue: DesignQueueItem[];
  archivedQueue: DesignQueueItem[];
  currentIndex: number;
  sessionActions: Record<string, ReviewAction>;
  isLoading: boolean;
  error: string | null;
  fetchQueue: () => Promise<void>;
  fetchArchived: () => Promise<void>;
  approveDesign: (id: string, productTypes?: string[]) => Promise<void>;
  rejectDesign: (id: string) => Promise<void>;
  archiveDesign: (id: string) => Promise<void>;
  unarchiveDesign: (id: string) => Promise<void>;
  revisitDesign: (id: string) => Promise<void>;
  delayDesign: (id: string, week: string) => Promise<void>;
  goToNext: () => void;
  goToPrevious: () => void;
  goToIndex: (index: number) => void;
  reset: () => void;
}

export const useReviewStore = create<ReviewState>((set, get) => ({
  queue: [],
  archivedQueue: [],
  currentIndex: 0,
  sessionActions: {},
  isLoading: false,
  error: null,

  fetchQueue: async () => {
    set({ isLoading: true, error: null });
    try {
      const queue = await getReviewQueue('active');
      set({ queue, isLoading: false, currentIndex: 0, sessionActions: {} });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchArchived: async () => {
    try {
      const archivedQueue = await getReviewQueue('archived');
      set({ archivedQueue });
    } catch { /* ignore */ }
  },

  approveDesign: async (id: string, productTypes?: string[]) => {
    set((s) => ({ sessionActions: { ...s.sessionActions, [id]: 'approved' } }));
    try {
      await apiApprove(id, productTypes);
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

  archiveDesign: async (id: string) => {
    set((s) => ({ sessionActions: { ...s.sessionActions, [id]: 'archived' } }));
    try {
      await apiArchive(id);
    } catch {
      set((s) => { const { [id]: _, ...rest } = s.sessionActions; return { sessionActions: rest }; });
    }
  },

  unarchiveDesign: async (id: string) => {
    try {
      await apiUnarchive(id);
      get().fetchQueue();
      get().fetchArchived();
    } catch { /* ignore */ }
  },

  revisitDesign: async (id: string) => {
    set((s) => ({ sessionActions: { ...s.sessionActions, [id]: 'revisited' } }));
    try {
      await apiRevisit(id);
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
  reset: () => set({ queue: [], archivedQueue: [], currentIndex: 0, sessionActions: {}, error: null }),
}));
