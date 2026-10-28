import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { Card, Icon, IconBadge, Pressy, Row, T } from '../../components/ui';
import { useSettings } from '../../store/settings';
import { spacing } from '../../theme/tokens';
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
      <Pressy onPress={open} accessibilityRole="button" accessibilityLabel={t('weather.pickLocation')}>
        <Card>
          <Row style={{ flexWrap: 'nowrap' }} gap={spacing.md}>
            <IconBadge name="map-marker-outline" size={40} />
            <View style={{ flex: 1 }}><T>{t('weather.pickLocation')}</T></View>
            <Icon name="chevron-right" color={colors.textMuted} />
          </Row>
        </Card>
      </Pressy>
    ) : null;
  }
  if (!q.data) {
    return <Card><T muted>{q.isError ? t('weather.unavailable') : '…'}</T></Card>;
  }
  const age = Date.now() - new Date(q.data.fetched_at).getTime();
  if (age > TOO_OLD_MS) return <Card tone="warning"><T>{t('weather.tooOld')}</T></Card>;
  const stale = age > STALE_MS || q.isError;
  const c = q.data.current;

  const stats = [
    c.humidity_pct !== null ? { icon: 'water-percent' as const, text: t('weather.humidity', { value: c.humidity_pct }) } : null,
    c.wind_kph !== null ? { icon: 'weather-windy' as const, text: t('weather.wind', { value: Math.round(c.wind_kph) }) } : null,
    c.rain_mm !== null ? { icon: 'weather-rainy' as const, text: t('weather.rain', { value: c.rain_mm }) } : null,
  ].filter((s): s is NonNullable<typeof s> => s !== null);

  const body = (
    <Card style={stale ? { opacity: 0.75 } : undefined}>
      <Row style={{ justifyContent: 'space-between', flexWrap: 'nowrap', alignItems: 'flex-start' }}>
        <View style={{ flex: 1, gap: 2 }}>
          <T v="overline" muted upper>{location.label}</T>
          <T v="display">{c.temp_c !== null ? `${Math.round(c.temp_c)}°` : '—'}</T>
          <T muted>{t(`weather.code.${codeKey(c.weather_code)}`)}</T>
        </View>
        <Icon name={codeIcon(c.weather_code)} size={48} color={colors.primary} />
      </Row>
      <Row gap={spacing.lg}>
        {stats.map((s) => (
          <Row key={s.icon} gap={spacing.xs}>
            <Icon name={s.icon} size={16} color={colors.textMuted} />
            <T v="caption" muted>{s.text}</T>
          </Row>
        ))}
      </Row>
      <Row>
        <T v="caption" muted>{t('weather.updated', { time: formatTime(q.data.fetched_at, i18n.language) })}</T>
        {stale && <T v="caption" color={colors.warning}>· {t('weather.notCurrent')}</T>}
      </Row>
    </Card>
  );
  return compact ? (
    <Pressy onPress={open} accessibilityRole="button" accessibilityLabel={t('weather.title')}>{body}</Pressy>
  ) : body;
}
