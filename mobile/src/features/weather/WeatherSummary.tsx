import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Pressable, View } from 'react-native';

import { Card, Icon, Row, T } from '../../components/ui';
import { useSettings } from '../../store/settings';
import { useTheme } from '../../theme/useTheme';
import { codeIcon, codeKey, formatTime, STALE_MS, TOO_OLD_MS, useWeather } from './weather';

export function WeatherSummary({ compact }: { compact?: boolean }) {
  const { t, i18n } = useTranslation();
  const { colors } = useTheme();
  const location = useSettings((s) => s.location);
  const q = useWeather();

  const open = () => router.navigate('/weather');
  if (!location) {
    return compact ? (
      <Pressable onPress={open} accessibilityRole="button"><Card><Row>
        <Icon name="map-marker-question" color={colors.primary} /><T>{t('weather.pickLocation')}</T>
      </Row></Card></Pressable>
    ) : null;
  }
  if (!q.data) {
    return <Card><T muted>{q.isError ? t('weather.unavailable') : '…'}</T></Card>;
  }
  const age = Date.now() - new Date(q.data.fetched_at).getTime();
  if (age > TOO_OLD_MS) return <Card tone="warning"><T>{t('weather.tooOld')}</T></Card>;
  const stale = age > STALE_MS || q.isError;
  const c = q.data.current;

  return (
    <Pressable onPress={compact ? open : undefined} disabled={!compact}>
      <Card style={stale ? { opacity: 0.75 } : undefined}>
        <Row style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
          <View style={{ flex: 1 }}>
            <T v="label" muted>{location.label}</T>
            <T v="display">{c.temp_c !== null ? `${Math.round(c.temp_c)}°C` : '—'}</T>
            <T>{t(`weather.code.${codeKey(c.weather_code)}`)}</T>
          </View>
          <Icon name={codeIcon(c.weather_code)} size={56} color={colors.primary} />
        </Row>
        <Row gap={16}>
          {c.humidity_pct !== null && <T v="label">{t('weather.humidity', { value: c.humidity_pct })}</T>}
          {c.wind_kph !== null && <T v="label">{t('weather.wind', { value: Math.round(c.wind_kph) })}</T>}
          {c.rain_mm !== null && <T v="label">{t('weather.rain', { value: c.rain_mm })}</T>}
        </Row>
        <Row>
          <T v="caption" muted>{t('weather.updated', { time: formatTime(q.data.fetched_at, i18n.language) })}</T>
          {stale && <T v="caption" color={colors.warning}>· {t('weather.notCurrent')}</T>}
        </Row>
      </Card>
    </Pressable>
  );
}
