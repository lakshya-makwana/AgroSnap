import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import { Button, Card, Icon, Row, Screen, T } from '../../components/ui';
import { WeatherSummary } from '../../features/weather/WeatherSummary';
import { useTheme } from '../../theme/useTheme';

export default function Home() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return (
    <Screen>
      <T v="display">{t('home.greeting')}</T>
      <T muted>{t('home.subtitle')}</T>
      <WeatherSummary compact />
      <Button label={t('home.scanCta')} icon="camera" onPress={() => router.navigate('/scan')} style={{ minHeight: 72 }} />
      <Card>
        <T v="heading">{t('home.tipsTitle')}</T>
        {(['one', 'two', 'three', 'four'] as const).map((k) => (
          <Row key={k} style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
            <Icon name="check-circle" color={colors.primary} />
            <T>{t(`tips.${k}`)}</T>
          </Row>
        ))}
      </Card>
    </Screen>
  );
}
