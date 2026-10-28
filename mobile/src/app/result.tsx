import { Redirect, router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, View } from 'react-native';
import Animated from 'react-native-reanimated';

import { Button, Card, IconBadge, List, Meter, Notice, Row, Screen, SectionLabel, Steps, T } from '../components/ui';
import { FeedbackCard } from '../features/detection/FeedbackCard';
import { speakResult, stopSpeaking } from '../features/detection/speech';
import type { Candidate } from '../services/api';
import { useScan } from '../store/scan';
import { useEnter } from '../theme/motion';
import { spacing } from '../theme/tokens';
import { useTheme } from '../theme/useTheme';

/** Confidence as bar + words. The percentage stays one tap away (UI_UX: farmers see the band first). */
function Confidence({ c }: { c: Candidate }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [showPct, setShowPct] = useState(false);
  const color = c.band === 'high' ? colors.primary : c.band === 'medium' ? colors.warning : colors.error;
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={`${t(`result.match_${c.band}`)}. ${t('result.showScore')}`}
      onPress={() => setShowPct((v) => !v)} style={{ minHeight: 44, justifyContent: 'center' }}>
      <Row style={{ flexWrap: 'nowrap' }} gap={spacing.md}>
        <Meter value={c.score} color={color} />
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
  const enter0 = useEnter(0);
  const enter1 = useEnter(1);
  const enter2 = useEnter(2);
  useFocusEffect(useCallback(() => () => stopSpeaking(), []));

  if (!result || !uri) return <Redirect href="/scan" />;
  const top = result.top_prediction;
  const status = result.status;

  const listen = () => {
    if (speaking) {
      stopSpeaking();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    speakResult(result, t, i18n.language, () => setSpeaking(false));
  };

  const hero = status === 'confident' ? (
    top.is_healthy ? (
      <Row style={{ flexWrap: 'nowrap' }} gap={spacing.md}>
        <IconBadge name="check" size={44} />
        <View style={{ flex: 1 }}><T v="title">{t('result.healthy', { crop: top.crop })}</T></View>
      </Row>
    ) : (
      <View style={{ gap: spacing.xs }}>
        <T v="overline" muted upper>{`${t('result.mostLikely')} · ${top.crop}`}</T>
        <T v="title">{top.disease}</T>
      </View>
    )
  ) : (
    <Row style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }} gap={spacing.md}>
      <IconBadge name={status === 'uncertain' ? 'help' : 'image-off-outline'} size={44} tone="muted" />
      <View style={{ flex: 1, gap: spacing.xs }}>
        <T v="title">{status === 'uncertain' ? t('result.uncertainTitle') : t('result.unsupportedTitle')}</T>
        {status === 'unsupported' && result.reason && (
          <T muted>{t(`result.reason_${result.reason}`, { defaultValue: '' })}</T>
        )}
      </View>
    </Row>
  );

  const others = status === 'confident' ? result.alternatives : [top, ...result.alternatives];

  return (
    <Screen>
      {result.is_demo && <Notice icon="flask-outline" text={t('common.demo')} />}

      <Animated.View style={enter0}>
        <Card>
          {hero}
          {status === 'confident' && <Confidence c={top} />}
          <Button kind="secondary" icon={speaking ? 'stop' : 'volume-high'}
            label={speaking ? t('result.stop') : t('result.listen')} onPress={listen} />
        </Card>
      </Animated.View>

      {result.crop_filter.mismatch && result.crop_filter.detected_crop && (
        <Notice icon="swap-horizontal" text={t('result.cropMismatch', { crop: result.crop_filter.detected_crop })} />
      )}

      {status !== 'unsupported' && others.length > 0 && (
        <Animated.View style={[{ gap: spacing.lg }, enter1]}>
          <SectionLabel>{status === 'confident' ? t('result.otherPossibilities') : t('result.uncertainBody')}</SectionLabel>
          <Card flush>
            <List>
              {others.map((c) => (
                <View key={c.class_id} style={{ paddingVertical: spacing.md, gap: 2 }}>
                  <T>{c.disease}</T>
                  <T v="caption" muted>{c.crop}</T>
                  <Confidence c={c} />
                </View>
              ))}
            </List>
          </Card>
          <T v="caption" muted>{result.score_explanation}</T>
        </Animated.View>
      )}

      {status !== 'confident' && (
        <Card>
          <Steps items={(['one', 'two', 'three', 'four'] as const).map((k) => t(`tips.${k}`))} />
        </Card>
      )}

      <Animated.View style={[{ gap: spacing.md }, enter2]}>
        {status === 'confident' && !top.is_healthy && !result.advisory_available && (
          <Notice icon="book-open-variant" tone="primary" text={t('result.noGuidance')} />
        )}
        <Notice icon="account-tie-outline" tone="primary" text={t('common.kvk')} />
      </Animated.View>

      {status !== 'unsupported' && <FeedbackCard result={result} uri={uri} crop={crop} />}

      <Button label={status === 'confident' ? t('result.scanAgain') : t('result.retakePhoto')} icon="camera-outline"
        onPress={() => router.dismissTo('/scan')} />
      <View style={{ height: spacing.sm, backgroundColor: colors.background }} />
    </Screen>
  );
}
