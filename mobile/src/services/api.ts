// Typed client for the AgroSnap API (docs/API.md). The app never sends class labels; the server owns them.
import { File } from 'expo-file-system';

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://10.0.2.2:8000/api/v1';

export type Band = 'high' | 'medium' | 'low';
export type Candidate = {
  class_id: number;
  class_key: string;
  crop: string;
  disease: string;
  is_healthy: boolean;
  score: number;
  band: Band;
};
export type Prediction = {
  status: 'confident' | 'uncertain' | 'unsupported';
  reason: string | null;
  top_prediction: Candidate;
  alternatives: Candidate[];
  crop_filter: { crop: string | null; applied: boolean; mismatch: boolean; detected_crop: string | null };
  score_explanation: string;
  advisory_available: boolean;
  model_version: string;
  is_demo: boolean;
  inference_ms: number;
};
export type CropItem = {
  crop: string;
  name: string;
  classes: { class_id: number; disease: string; is_healthy: boolean }[];
};
export type ModelInfo = {
  model_version: string;
  is_demo: boolean;
  compression: { variant: string; size_MB: number; compression_x: number } | null;
};
export type Weather = {
  location: { lat: number; lon: number };
  fetched_at: string;
  current: { temp_c: number | null; humidity_pct: number | null; rain_mm: number | null; wind_kph: number | null; weather_code: number | null };
  hourly: { time: string; temp_c: number; rain_chance_pct: number | null; weather_code: number }[];
  daily: { date: string; max_c: number; min_c: number; rain_mm: number; rain_chance_pct: number | null; weather_code: number }[];
};

export class ApiError extends Error {
  constructor(public code: string, message: string, public status = 0, public retryable = false) {
    super(message);
  }
}

type Options = { method?: string; body?: FormData; headers?: Record<string, string>; timeoutMs?: number; lang: string };

async function request<T>(path: string, { method = 'GET', body, headers = {}, timeoutMs = 15000, lang }: Options): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      body,
      headers: { Accept: 'application/json', 'Accept-Language': lang, ...headers },
      signal: controller.signal,
    });
  } catch (e) {
    const aborted = e instanceof Error && e.name === 'AbortError';
    throw new ApiError(aborted ? 'TIMEOUT' : 'NETWORK', String(e), 0, true);
  } finally {
    clearTimeout(timer);
  }
  if (res.ok) return (await res.json()) as T;
  let code = res.status >= 500 ? 'SERVER' : 'UNKNOWN';
  let message = res.statusText;
  try {
    const err = (await res.json()) as { error?: { code?: string; message?: string } };
    code = err.error?.code ?? code;
    message = err.error?.message ?? message;
  } catch {
    // non-JSON error body: keep the status-based code
  }
  throw new ApiError(code, message, res.status, res.status >= 500);
}

function imagePart(uri: string): Blob {
  // Expo's fetch rejects the old React Native {uri, name, type} descriptor ("Unsupported FormDataPart
  // implementation"). An expo-file-system File is a real Blob, which it uploads as a file part.
  return new File(uri) as unknown as Blob;
}

export const api = {
  crops: (lang: string) => request<{ items: CropItem[] }>('/crops', { lang }),
  modelInfo: (lang: string) => request<ModelInfo>('/model-info', { lang }),
  weather: (lat: number, lon: number, lang: string) =>
    request<Weather>(`/weather?lat=${lat.toFixed(4)}&lon=${lon.toFixed(4)}`, { lang }),

  predict(args: { uri: string; source: 'camera' | 'gallery'; crop: string | null; idempotencyKey: string; lang: string }) {
    const form = new FormData();
    form.append('image', imagePart(args.uri), 'leaf.jpg');
    form.append('source', args.source);
    if (args.crop) form.append('crop', args.crop);
    return request<Prediction>('/predictions', {
      method: 'POST', body: form, timeoutMs: 30000, lang: args.lang,
      headers: { 'Idempotency-Key': args.idempotencyKey },
    });
  },

  feedback(args: {
    verdict: 'correct' | 'wrong' | 'unsure'; predictedClassId: number; correctClassId: number | null;
    crop: string | null; modelVersion: string; sharePhoto: boolean; uri: string; lang: string;
  }) {
    const form = new FormData();
    form.append('verdict', args.verdict);
    form.append('predicted_class_id', String(args.predictedClassId));
    form.append('model_version', args.modelVersion);
    if (args.correctClassId !== null) form.append('correct_class_id', String(args.correctClassId));
    if (args.crop) form.append('crop', args.crop);
    form.append('share_photo', args.sharePhoto ? 'true' : 'false');
    if (args.sharePhoto) form.append('image', imagePart(args.uri), 'leaf.jpg');
    return request<{ id: string; photo_stored: boolean }>('/feedback', { method: 'POST', body: form, timeoutMs: 30000, lang: args.lang });
  },
};
