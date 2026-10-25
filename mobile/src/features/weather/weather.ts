import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { api } from '../../services/api';
import { useSettings } from '../../store/settings';

export const CITIES = [
  { label: 'Delhi', lat: 28.61, lon: 77.21 }, { label: 'Mumbai', lat: 19.08, lon: 72.88 },
  { label: 'Pune', lat: 18.52, lon: 73.86 }, { label: 'Ahmedabad', lat: 23.02, lon: 72.57 },
  { label: 'Jaipur', lat: 26.91, lon: 75.79 }, { label: 'Lucknow', lat: 26.85, lon: 80.95 },
  { label: 'Patna', lat: 25.59, lon: 85.14 }, { label: 'Bhopal', lat: 23.26, lon: 77.41 },
  { label: 'Hyderabad', lat: 17.39, lon: 78.49 }, { label: 'Bengaluru', lat: 12.97, lon: 77.59 },
  { label: 'Chennai', lat: 13.08, lon: 80.27 }, { label: 'Kolkata', lat: 22.57, lon: 88.36 },
];

export const STALE_MS = 60 * 60 * 1000; // OFFLINE_AND_NETWORK §3
export const TOO_OLD_MS = 24 * 60 * 60 * 1000;

// WMO weather codes (Open-Meteo) -> i18n key
export function codeKey(code: number | null | undefined): string {
  if (code === null || code === undefined) return 'unknown';
  if (code === 0) return 'clear';
  if (code <= 2) return 'partly';
  if (code === 3) return 'cloudy';
  if (code === 45 || code === 48) return 'fog';
  if (code >= 51 && code <= 57) return 'drizzle';
  if ((code >= 61 && code <= 67) || (code >= 71 && code <= 77)) return 'rain';
  if (code >= 80 && code <= 86) return 'showers';
  if (code >= 95) return 'storm';
  return 'unknown';
}

export function codeIcon(code: number | null | undefined) {
  const k = codeKey(code);
  return ({ clear: 'weather-sunny', partly: 'weather-partly-cloudy', cloudy: 'weather-cloudy', fog: 'weather-fog',
    drizzle: 'weather-rainy', rain: 'weather-pouring', showers: 'weather-pouring', storm: 'weather-lightning-rainy',
    unknown: 'weather-cloudy-alert' } as const)[k as 'clear'];
}

export function useWeather() {
  const location = useSettings((s) => s.location);
  const { i18n } = useTranslation();
  return useQuery({
    queryKey: ['weather', location?.lat, location?.lon],
    queryFn: () => api.weather(location!.lat, location!.lon, i18n.language),
    enabled: !!location,
    staleTime: 15 * 60 * 1000,
    refetchOnMount: true,
  });
}

export function formatTime(iso: string, lang: string) {
  return new Intl.DateTimeFormat(lang === 'hi' ? 'hi-IN' : 'en-IN', { hour: 'numeric', minute: '2-digit' }).format(new Date(iso));
}
