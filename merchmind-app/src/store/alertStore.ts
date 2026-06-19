import { create } from 'zustand';
import type { Alert } from '../types/api';
import { listAlerts, resolveAlert } from '../api/alerts';

interface AlertState {
  alerts: Alert[];
  isLoading: boolean;
  error: string | null;
  unreadCount: number;

  fetchAlerts: () => Promise<void>;
  resolveAlert: (alertId: string) => Promise<void>;
}

export const useAlertStore = create<AlertState>((set, get) => ({
  alerts: [],
  isLoading: false,
  error: null,
  unreadCount: 0,

  fetchAlerts: async () => {
    set({ isLoading: true, error: null });
    try {
      const alerts = await listAlerts({ resolved: false });
      set({ alerts, unreadCount: alerts.length, isLoading: false });
    } catch (e: unknown) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  resolveAlert: async (alertId: string) => {
    set(state => ({
      alerts: state.alerts.filter(a => a.id !== alertId),
      unreadCount: Math.max(0, state.unreadCount - 1),
    }));
    try {
      await resolveAlert(alertId);
    } catch {
      await get().fetchAlerts();
      throw new Error('Failed to resolve alert');
    }
  },
}));
