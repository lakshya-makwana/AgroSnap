import * as Speech from 'expo-speech';
import type { TFunction } from 'i18next';

import type { Prediction } from '../../services/api';

// [A3] Read the result aloud in the app language.
export async function hasVoiceFor(lang: string): Promise<boolean> {
  try {
    const voices = await Speech.getAvailableVoicesAsync();
    return voices.length === 0 || voices.some((v) => v.language.toLowerCase().startsWith(lang));
  } catch {
    return true; // cannot tell; let the system TTS try
  }
}

export function resultSpeech(r: Prediction, t: TFunction): string {
  const top = r.top_prediction;
  const band = t(`result.match_${top.band}`);
  if (r.status === 'unsupported') {
    return t('result.speakUnsupported', { reason: r.reason ? t(`result.reason_${r.reason}`, { defaultValue: '' }) : '' });
  }
  if (r.status === 'uncertain') {
    const options = [top, ...r.alternatives].map((c) => `${c.disease} (${c.crop})`).join(', ');
    return t('result.speakUncertain', { options });
  }
  if (top.is_healthy) return t('result.speakHealthy', { crop: top.crop, band });
  return t('result.speakConfident', { disease: top.disease, crop: top.crop, band, kvk: t('common.kvk') });
}

export function speakResult(r: Prediction, t: TFunction, lang: string, onDone: () => void) {
  Speech.stop();
  Speech.speak(resultSpeech(r, t), {
    language: lang === 'hi' ? 'hi-IN' : 'en-IN', rate: 0.9, onDone, onStopped: onDone, onError: onDone,
  });
}

export const stopSpeaking = () => Speech.stop();
