import * as Location from 'expo-location';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ScrollView, View } from 'react-native';

import { Button, Card, Chip, Icon, List, Notice, Row, Screen, SectionLabel, T } from '../../components/ui';
import { spacing } from '../../theme/tokens';
import { WeatherSummary } from '../../features/weather/WeatherSummary';
import { CITIES, codeIcon, formatTime, useWeather } from '../../features/weather/weather';
import { useSettings } from '../../store/settings';
import { useTheme } from '../../theme/useTheme';

export default function WeatherScreen() {
  const { t, i18n } = useTranslation();
  const { colors } = useTheme();
  const { location, setLocation } = useSettings();
  const q = useWeather();
  const [denied, setDenied] = useState(false);
  const [locating, setLocating] = useState(false);

  // Location is requested only when the farmer taps the button (PHASES 6 exit criteria).
  const useDevice = async () => {
    setLocating(true);
    try {
      const { granted } = await Location.requestForegroundPermissionsAsync();
      if (!granted) {
        setDenied(true);
        return;
      }
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      setDenied(false);
      setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude, label: t('weather.useMyLocation'), source: 'device' });
    } finally {
      setLocating(false);
    }
  };

  const fmtDay = (d: string) =>
    new Intl.DateTimeFormat(i18n.language === 'hi' ? 'hi-IN' : 'en-IN', { weekday: 'short', day: 'numeric' }).format(new Date(d));

  return (
    <Screen>
      <WeatherSummary />
      {q.isError && !q.data && <Notice icon="cloud-alert" tone="error" text={t('weather.unavailable')} />}
      {q.data && (
        <>
          <SectionLabel>{t('weather.next24')}</SectionLabel>
          <Card>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              <Row gap={20} style={{ flexWrap: 'nowrap' }}>
                {q.data.hourly.map((h) => (
                  <View key={h.time} style={{ alignItems: 'center', gap: 4 }}>
                    <T v="caption" muted>{formatTime(h.time, i18n.language)}</T>
                    <Icon name={codeIcon(h.weather_code)} color={colors.primary} />
                    <T v="label">{Math.round(h.temp_c)}°</T>
                    {h.rain_chance_pct !== null && <T v="caption" color={colors.info}>{h.rain_chance_pct}%</T>}
                  </View>
                ))}
              </Row>
            </ScrollView>
          </Card>
          <SectionLabel>{t('weather.next7')}</SectionLabel>
          <Card flush>
            <List>
              {q.data.daily.map((d) => (
                <Row key={d.date} style={{ justifyContent: 'space-between', flexWrap: 'nowrap', minHeight: 52 }}>
                  <View style={{ width: 96 }}><T>{fmtDay(d.date)}</T></View>
                  <Icon name={codeIcon(d.weather_code)} color={colors.primary} />
                  <View style={{ width: 72, alignItems: 'flex-end' }}>
                    <T v="caption" color={colors.info}>{d.rain_chance_pct !== null ? t('weather.rainChance', { value: d.rain_chance_pct }) : ''}</T>
                  </View>
                  <T v="label"><T v="label" muted>{Math.round(d.min_c)}°</T>  {Math.round(d.max_c)}°</T>
                </Row>
              ))}
            </List>
          </Card>
        </>
      )}
      <Card>
        <Button kind="secondary" icon="crosshairs-gps" label={t('weather.useMyLocation')} loading={locating} onPress={useDevice} />
        {denied && <T v="label" color={colors.warning}>{t('weather.locationDenied')}</T>}
        <View style={{ height: spacing.xs }} />
        <T v="overline" muted upper>{t('weather.chooseCity')}</T>
        <Row>
          {CITIES.map((c) => (
            <Chip key={c.label} label={c.label} selected={location?.label === c.label}
              onPress={() => setLocation({ ...c, source: 'manual' })} />
          ))}
        </Row>
      </Card>
    </Screen>
  );
}
