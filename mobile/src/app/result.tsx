import { Redirect, router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, View } from 'react-native';

import { Button, Card, Icon, Notice, Row, Screen, T } from '../components/ui';
import { FeedbackCard } from '../features/detection/FeedbackCard';
import { speakResult, stopSpeaking } from '../features/detection/speech';
import type { Candidate } from '../services/api';
import { useScan } from '../store/scan';
import { useTheme } from '../theme/useTheme';

function MatchBadge({ c }: { c: Candidate }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [showPct, setShowPct] = useState(false);
  const color = c.band === 'high' ? colors.primary : c.band === 'medium' ? colors.warning : colors.error;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={t('result.showScore')} onPress={() => setShowPct((v) => !v)}
      style={{ minHeight: 48, justifyContent: 'center' }}>
      <Row>
        <Icon name={c.band === 'high' ? 'signal-cellular-3' : c.band === 'medium' ? 'signal-cellular-2' : 'signal-cellular-1'}
          color={color} />
        <T v="label" color={color}>
          {t(`result.match_${c.band}`)}{showPct ? ` · ${t('result.scorePercent', { value: Math.round(c.score * 100) })}` : ''}
        </T>
      </Row>
    </Pressable>
  );
}

export default function Result() {
  const { t, i18n } = useTranslation();
  const { colors } = useTheme();
  const { result, uri, crop } = useScan();
  const [speaking, setSpeaking] = useState(false);
  useFocusEffect(useCallback(() => () => stopSpeaking(), []));

  if (!result || !uri) return <Redirect href="/scan" />;
  const top = result.top_prediction;
  const status = result.status;
  const header = {
    confident: { icon: 'check-decagram' as const, tone: 'primary' as const, color: colors.primaryDark,
      title: top.is_healthy ? t('result.healthy', { crop: top.crop }) : t('result.likely', { disease: top.disease, crop: top.crop }) },
    uncertain: { icon: 'help-circle' as const, tone: 'warning' as const, color: colors.warning, title: t('result.uncertainTitle') },
    unsupported: { icon: 'image-off' as const, tone: 'error' as const, color: colors.error, title: t('result.unsupportedTitle') },
  }[status];

  const listen = () => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    speakResult(result, t, i18n.language, () => setSpeaking(false));
  };

  return (
    <Screen>
      {result.is_demo && <Notice icon="flask" text={t('common.demo')} />}
      <Card tone={header.tone}>
        <Row style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
          <Icon name={header.icon} color={header.color} size={32} />
          <View style={{ flex: 1 }}><T v="title" color={header.color}>{header.title}</T></View>
        </Row>
        {status === 'confident' && <MatchBadge c={top} />}
        {status === 'unsupported' && result.reason && (
          <T>{t(`result.reason_${result.reason}`, { defaultValue: '' })}</T>
        )}
        <Button kind="secondary" icon={speaking ? 'stop-circle' : 'volume-high'}
          label={speaking ? t('result.stop') : t('result.listen')} onPress={listen} />
      </Card>

      {result.crop_filter.mismatch && result.crop_filter.detected_crop && (
        <Notice icon="swap-horizontal" text={t('result.cropMismatch', { crop: result.crop_filter.detected_crop })} />
      )}

      {status !== 'unsupported' && (
        <Card>
          <T v="heading">{status === 'confident' ? t('result.otherPossibilities') : t('result.uncertainBody')}</T>
          {(status === 'confident' ? result.alternatives : [top, ...result.alternatives]).map((c) => (
            <View key={c.class_id} style={{ borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 8 }}>
              <T>{c.disease} · {c.crop}</T>
              <MatchBadge c={c} />
            </View>
          ))}
          <T v="caption" muted>{result.score_explanation}</T>
        </Card>
      )}

      {status !== 'confident' && (
        <Card>
          {(['one', 'two', 'three', 'four'] as const).map((k) => (
            <Row key={k} style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
              <Icon name="lightbulb-on-outline" color={colors.primary} size={20} />
              <View style={{ flex: 1 }}><T v="label">{t(`tips.${k}`)}</T></View>
            </Row>
          ))}
        </Card>
      )}

      {status === 'confident' && !top.is_healthy && !result.advisory_available && (
        <Notice icon="book-open-variant" tone="primary" text={t('result.noGuidance')} />
      )}
      <Notice icon="account-tie" tone="primary" text={t('common.kvk')} />

      {status !== 'unsupported' && <FeedbackCard result={result} uri={uri} crop={crop} />}

      <Button label={status === 'confident' ? t('result.scanAgain') : t('result.retakePhoto')} icon="camera"
        onPress={() => router.dismissTo('/scan')} />
    </Screen>
  );
}
