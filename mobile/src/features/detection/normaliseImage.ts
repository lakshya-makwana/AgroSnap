import { File } from 'expo-file-system';
import { Platform } from 'react-native';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';

// docs/SCAN_FLOW.md §4. The server repeats every check; this only shrinks uploads and converts HEIC/PNG to JPEG.
export const MIN_SIDE = 224;
export const MAX_LONG_EDGE = 1600;
export const MAX_BYTES = 8 * 1024 * 1024;

export class NormaliseError extends Error {
  constructor(public reason: 'tooSmall' | 'tooLarge' | 'processingError') {
    super(reason);
  }
}

export function targetSize(width: number, height: number): { width: number; height: number } | null {
  const long = Math.max(width, height);
  if (long <= MAX_LONG_EDGE) return null; // never upscale
  const k = MAX_LONG_EDGE / long;
  return { width: Math.round(width * k), height: Math.round(height * k) };
}

export async function normaliseImage(uri: string, width: number, height: number): Promise<string> {
  if (Math.min(width, height) < MIN_SIDE) throw new NormaliseError('tooSmall');
  try {
    for (const compress of [0.85, 0.7]) {
      const ctx = ImageManipulator.manipulate(uri);
      const size = targetSize(width, height);
      if (size) ctx.resize(size);
      const rendered = await ctx.renderAsync();
      const saved = await rendered.saveAsync({ format: SaveFormat.JPEG, compress });
      // Web has no file system: the browser hands us a blob URL, and the server re-checks the size anyway.
      if (Platform.OS === 'web' || new File(saved.uri).size <= MAX_BYTES) return saved.uri;
    }
  } catch {
    throw new NormaliseError('processingError');
  }
  throw new NormaliseError('tooLarge');
}
