import { getLocales } from 'expo-localization';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import type { Language } from '../store/settings';
import en from './locales/en.json';
import hi from './locales/hi.json';

export const LANGUAGES: { code: Language; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
];

// Precedence (docs/I18N.md): saved choice -> device language if supported -> English.
export function resolveLanguage(saved: Language | null): Language {
  if (saved) return saved;
  const device = getLocales()[0]?.languageCode;
  return device === 'hi' ? 'hi' : 'en';
}

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, hi: { translation: hi } },
  lng: resolveLanguage(null),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export default i18n;
