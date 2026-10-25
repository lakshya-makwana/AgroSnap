import { randomUUID } from 'expo-crypto';
import { create } from 'zustand';

import type { Prediction } from '../services/api';

// The scan in progress: one normalised image, one idempotency key (docs/SCAN_FLOW.md §6).
type ScanState = {
  uri: string | null;
  source: 'camera' | 'gallery' | null;
  crop: string | null;
  idempotencyKey: string | null;
  result: Prediction | null;
  setImage: (uri: string, source: 'camera' | 'gallery', crop: string | null) => void;
  setResult: (r: Prediction) => void;
  reset: () => void;
};

export const useScan = create<ScanState>()((set) => ({
  uri: null,
  source: null,
  crop: null,
  idempotencyKey: null,
  result: null,
  setImage: (uri, source, crop) => set({ uri, source, crop, idempotencyKey: randomUUID(), result: null }),
  setResult: (result) => set({ result }),
  reset: () => set({ uri: null, source: null, crop: null, idempotencyKey: null, result: null }),
}));
