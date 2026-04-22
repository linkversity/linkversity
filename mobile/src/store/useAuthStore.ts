import { create } from 'zustand';
import { MMKV } from 'react-native-mmkv';

// Safely initialize MMKV
let storage: {
  getString: (key: string) => string | undefined;
  set: (key: string, value: string | number | boolean | Uint8Array) => void;
  delete: (key: string) => void;
};

try {
  storage = new MMKV();
} catch (e) {
  console.warn('MMKV could not be initialized, using fallback storage', e);
  const mockStorage: Record<string, string> = {};
  storage = {
    getString: (key: string) => mockStorage[key],
    set: (key: string, value: any) => { mockStorage[key] = String(value); },
    delete: (key: string) => { delete mockStorage[key]; },
  };
}

interface User {
  id: number;
  username: string;
  email: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

export const useAuthStore = create<AuthState>((set) => {
  const storedToken = storage.getString('auth_token');
  const storedUser = storage.getString('auth_user');

  return {
    token: storedToken || null,
    user: storedUser ? JSON.parse(storedUser) : null,
    isAuthenticated: !!storedToken,
    setAuth: (token, user) => {
      storage.set('auth_token', token);
      storage.set('auth_user', JSON.stringify(user));
      set({ token, user, isAuthenticated: true });
    },
    logout: () => {
      storage.delete('auth_token');
      storage.delete('auth_user');
      set({ token: null, user: null, isAuthenticated: false });
    },
  };
});
