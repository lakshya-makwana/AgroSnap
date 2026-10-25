import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export type Language = 'en' | 'hi';
export type SavedLocation = { lat: number; lon: number; label: string; source: 'device' | 'manual' };

type SettingsState = {
  language: Language | null; // null = follow the device language
  highContrast: boolean;
  largeText: boolean;
  lastCrop: string | null; // [A1] remembered between scans; null = "Not sure"
  location: SavedLocation | null;
  setLanguage: (l: Language) => void;
  setHighContrast: (v: boolean) => void;
  setLargeText: (v: boolean) => void;
  setLastCrop: (c: string | null) => void;
  setLocation: (l: SavedLocation) => void;
};

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      language: null,
      highContrast: false,
      largeText: false,
      lastCrop: null,
      location: null,
      setLanguage: (language) => set({ language }),
      setHighContrast: (highContrast) => set({ highContrast }),
      setLargeText: (largeText) => set({ largeText }),
      setLastCrop: (lastCrop) => set({ lastCrop }),
      setLocation: (location) => set({ location }),
    }),
    { name: 'agrosnap-settings', storage: createJSONStorage(() => AsyncStorage) },
  ),
);
