import { create } from 'zustand';
import { apiClient } from '../api/client';

export interface Path {
  id: number;
  title: string;
  slug: string;
  is_visible: boolean;
  section_count: number;
}

export interface Section {
  id: number;
  title: string;
  link_count?: number;
  links?: Link[];
}

export interface Link {
  id: number;
  url: string;
  title: string | null;
  description: string | null;
  image_url: string | null;
}

interface LinkState {
  paths: Path[];
  totalPaths: number;
  totalPages: number;
  currentPage: number;
  sections: Record<number, Section[]>; // pathId -> sections
  isLoading: boolean;
  error: string | null;
  fetchPaths: (page?: number) => Promise<void>;
  fetchSections: (pathId: number) => Promise<void>;
  fetchPathContent: (pathId: number) => Promise<any>;
  saveLink: (url: string, sectionId: number, title?: string) => Promise<boolean>;
  createPath: (title: string, isVisible?: boolean) => Promise<boolean>;
  createSection: (title: string, pathId: number) => Promise<boolean>;
}

export const useLinkStore = create<LinkState>((set) => ({
  paths: [],
  totalPaths: 0,
  totalPages: 0,
  currentPage: 1,
  sections: {},
  isLoading: false,
  error: null,

  fetchPaths: async (page = 1) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.get('/slack/api/paths', {
        params: { page, per_page: 10 },
      });
      set({ 
        paths: response.data.items, 
        totalPaths: response.data.total,
        totalPages: response.data.pages,
        currentPage: response.data.current_page,
        isLoading: false 
      });
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

  fetchPathContent: async (pathId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiClient.get(`/slack/api/path/${pathId}/content`);
      set({ isLoading: false });
      return response.data;
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      return null;
    }
  },

  saveLink: async (url, sectionId, title) => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.post('/slack/api/save-link', {
        url,
        section_id: sectionId,
        title,
      });
      set({ isLoading: false });
      return true;
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      return false;
    }
  },

  createPath: async (title, isVisible = true) => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.post('/slack/api/paths', {
        title,
        is_visible: isVisible,
      });
      set({ isLoading: false });
      return true;
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      return false;
    }
  },

  createSection: async (title, pathId) => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.post('/slack/api/sections', {
        title,
        path_id: pathId,
      });
      set({ isLoading: false });
      return true;
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      return false;
    }
  },
}));
