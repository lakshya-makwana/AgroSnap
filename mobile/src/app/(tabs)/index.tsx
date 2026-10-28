import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Card, Icon, Pressy, Screen, SectionLabel, Steps, T } from '../../components/ui';
import { WeatherSummary } from '../../features/weather/WeatherSummary';
import { radius, spacing } from '../../theme/tokens';
import { useTheme } from '../../theme/useTheme';

export default function Home() {
  const { t, i18n } = useTranslation();
  const { colors, highContrast } = useTheme();
  const insets = useSafeAreaInsets();
  const today = new Intl.DateTimeFormat(i18n.language === 'hi' ? 'hi-IN' : 'en-IN',
    { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
  return (
    <Screen>
      <View style={{ paddingTop: insets.top + spacing.sm, gap: spacing.xs }}>
        <T v="overline" muted upper>{today}</T>
        <T v="display">{t('home.greeting')}</T>
      </View>

      <Pressy
        accessibilityRole="button"
        accessibilityLabel={t('home.scanCta')}
        accessibilityHint={t('home.subtitle')}
        onPress={() => router.navigate('/scan')}
        style={[styles.hero, { backgroundColor: colors.primary }, highContrast && { borderWidth: 2, borderColor: colors.border }]}
      >
        <View style={{ flex: 1, gap: spacing.xs }}>
          <T v="title" color={colors.onPrimary}>{t('home.scanCta')}</T>
          <T v="label" color="rgba(255,255,255,0.78)">{t('home.subtitle')}</T>
        </View>
        <View style={styles.heroIcon}>
          <Icon name="camera-outline" color={colors.primary} size={26} />
        </View>
      </Pressy>

      <WeatherSummary compact />

      <SectionLabel>{t('home.tipsTitle')}</SectionLabel>
      <Card>
        <Steps items={(['one', 'two', 'three', 'four'] as const).map((k) => t(`tips.${k}`))} />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { borderRadius: radius.card, padding: spacing.xl, minHeight: 128, flexDirection: 'row', alignItems: 'center',
    gap: spacing.lg },
  heroIcon: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#FFFFFF', alignItems: 'center',
    justifyContent: 'center' },
});
