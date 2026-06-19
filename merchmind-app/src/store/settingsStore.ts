import { create } from 'zustand';
import type { AppSettings } from '../types/api';
import { getSettings, updateSettings } from '../api/settings';

interface SettingsState {
  settings: AppSettings | null;
  isLoading: boolean;
  error: string | null;

  fetchSettings: () => Promise<void>;
  updateSettings: (updates: Partial<AppSettings>) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  isLoading: false,
  error: null,

  fetchSettings: async () => {
    set({ isLoading: true, error: null });
    try {
      const settings = await getSettings();
      set({ settings, isLoading: false });
    } catch (e: unknown) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  updateSettings: async (updates: Partial<AppSettings>) => {
    set(state => ({
      settings: state.settings ? { ...state.settings, ...updates } : null,
    }));
    try {
      const updated = await updateSettings(updates);
      set({ settings: updated });
    } catch (e: unknown) {
      await useSettingsStore.getState().fetchSettings();
      throw new Error('Failed to update settings');
    }
  },
}));
