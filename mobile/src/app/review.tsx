import { useMutation } from '@tanstack/react-query';
import * as Haptics from 'expo-haptics';
import { Image } from 'expo-image';
import { Redirect, router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, View } from 'react-native';

import { Button, Card, IconBadge, Notice, Row, Screen, T, useOnline } from '../components/ui';
import { useCrops } from '../features/detection/useCrops';
import { ApiError, api } from '../services/api';
import { useScan } from '../store/scan';
import { radius, spacing } from '../theme/tokens';
import { useTheme } from '../theme/useTheme';

export default function Review() {
  const { t, i18n } = useTranslation();
  const { colors, elevated } = useTheme();
  const online = useOnline();
  const { uri, source, crop, idempotencyKey, setResult } = useScan();
  const crops = useCrops();

  const detect = useMutation({
    // Same file and same idempotency key on every retry: the server never runs it twice (SCAN_FLOW §6).
    mutationFn: () => api.predict({ uri: uri!, source: source!, crop, idempotencyKey: idempotencyKey!, lang: i18n.language }),
    retry: (count, err) => count < 1 && err instanceof ApiError && err.retryable,
    onSuccess: (r) => {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setResult(r);
      router.replace('/result');
    },
    onError: () => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error),
  });

  if (!uri || !source || !idempotencyKey) return <Redirect href="/scan" />;
  const cropName = crop ? crops.data?.find((c) => c.crop === crop)?.name ?? crop : t('crop.notSure');
  const errorCode = detect.error instanceof ApiError ? detect.error.code : 'UNKNOWN';

  return (
    <Screen>
      <View style={[{ borderRadius: radius.card, overflow: 'hidden', backgroundColor: colors.surface }, elevated]}>
        <Image source={{ uri }} contentFit="cover" transition={150} style={{ width: '100%', aspectRatio: 1 }}
          accessibilityLabel={t('review.title')} />
      </View>
      <Card>
        <Row style={{ flexWrap: 'nowrap' }} gap={spacing.md}>
          <IconBadge name="sprout-outline" size={40} />
          <View style={{ flex: 1 }}><T v="heading">{t('review.cropLabel', { crop: cropName })}</T></View>
        </Row>
      </Card>
      {!online && <Notice icon="wifi-off" text={t('review.offlineMessage')} />}
      {detect.isError && <Notice icon="alert-circle-outline" tone="error" text={t(`errors.${errorCode}`, { defaultValue: t('errors.UNKNOWN') })} />}
      {detect.isPending && (
        <Row style={{ justifyContent: 'center' }}>
          <ActivityIndicator color={colors.textMuted} size="small" />
          <T v="label" muted>{t('review.checking')}</T>
        </Row>
      )}
      <Button
        label={online ? (detect.isError ? t('common.retry') : t('review.detect')) : t('review.detectOffline')}
        icon="magnify-scan"
        loading={detect.isPending}
        disabled={detect.isPending || !online}
        onPress={() => detect.mutate()}
      />
      <Button
        kind="secondary"
        label={source === 'camera' ? t('review.retake') : t('review.chooseAnother')}
        icon={source === 'camera' ? 'camera-retake-outline' : 'image-multiple-outline'}
        disabled={detect.isPending}
        onPress={() => router.back()}
      />
    </Screen>
  );
}
