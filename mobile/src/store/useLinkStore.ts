import { create } from 'zustand';
import { apiClient } from '../api/client';

export interface Path {
  id: number;
  title: string;
}

export interface Section {
  id: number;
  title: string;
}

interface LinkState {
  paths: Path[];
  sections: Record<number, Section[]>; // pathId -> sections
  isLoading: boolean;
  error: string | null;
  fetchPaths: () => Promise<void>;
  fetchSections: (pathId: number) => Promise<void>;
  saveLink: (url: string, sectionId: number) => Promise<boolean>;
}

export const useLinkStore = create<LinkState>((set) => ({
  paths: [],
  sections: {},
  isLoading: false,
  error: null,

  fetchPaths: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.get('/slack/api/paths');
      set({ paths: response.data, isLoading: false });
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
    }
  },

  fetchSections: async (pathId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.get('/slack/api/sections', {
        params: { path_id: pathId },
      });
      set((state) => ({
        sections: { ...state.sections, [pathId]: response.data },
        isLoading: false,
      }));
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
    }
  },

  saveLink: async (url, sectionId) => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.post('/slack/api/save-link', {
        url,
        section_id: sectionId,
      });
      set({ isLoading: false });
      return true;
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      return false;
    }
  },
}));
