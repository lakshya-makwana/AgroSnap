import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable } from 'react-native';

import { Button, Card, Chip, Icon, Notice, Row, T } from '../../components/ui';
import { api, type Prediction } from '../../services/api';
import { useTheme } from '../../theme/useTheme';
import { useCrops } from './useCrops';

type Verdict = 'correct' | 'wrong' | 'unsure';

// [A2] "Was this correct?" Photos are shared only if the farmer ticks the box (off by default).
export function FeedbackCard({ result, uri, crop }: { result: Prediction; uri: string; crop: string | null }) {
  const { t, i18n } = useTranslation();
  const { colors } = useTheme();
  const crops = useCrops();
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [correctId, setCorrectId] = useState<number | null>(null);
  const [share, setShare] = useState(false);
  const top = result.top_prediction;
  const cropKey = crop ?? result.crop_filter.crop;
  const options = (crops.data ?? []).filter((c) => !cropKey || c.crop === cropKey);

  const send = useMutation({
    mutationFn: () => api.feedback({
      verdict: verdict === 'wrong' && correctId === null ? 'unsure' : verdict!,
      predictedClassId: top.class_id,
      correctClassId: verdict === 'wrong' ? correctId : null,
      crop: cropKey, modelVersion: result.model_version, sharePhoto: share, uri, lang: i18n.language,
    }),
  });

  if (send.isSuccess) return <Notice icon="heart" tone="primary" text={t('feedback.thanks')} />;

  return (
    <Card>
      <T v="heading">{t('feedback.question')}</T>
      <Row>
        <Chip label={t('feedback.yes')} selected={verdict === 'correct'} onPress={() => setVerdict('correct')} />
        <Chip label={t('feedback.no')} selected={verdict === 'wrong'} onPress={() => setVerdict('wrong')} />
        <Chip label={t('feedback.unsure')} selected={verdict === 'unsure'} onPress={() => setVerdict('unsure')} />
      </Row>
      {verdict === 'wrong' && (
        <>
          <T v="label">{t('feedback.pickCorrect')}</T>
          <Row>
            {options.flatMap((c) => c.classes.filter((k) => k.class_id !== top.class_id).map((k) => (
              <Chip key={k.class_id} label={cropKey ? k.disease : `${c.name}: ${k.disease}`}
                selected={correctId === k.class_id} onPress={() => setCorrectId(k.class_id)} />
            )))}
            <Chip label={t('feedback.dontKnow')} selected={correctId === null} onPress={() => setCorrectId(null)} />
          </Row>
        </>
      )}
      {verdict && (
        <>
          <Pressable accessibilityRole="checkbox" accessibilityState={{ checked: share }} onPress={() => setShare((v) => !v)}
            style={{ flexDirection: 'row', gap: 8, alignItems: 'flex-start', minHeight: 48, paddingTop: 8 }}>
            <Icon name={share ? 'checkbox-marked' : 'checkbox-blank-outline'} color={colors.primary} size={28} />
            <T v="label">{t('feedback.sharePhoto')}{'\n'}<T v="caption" muted>{t('feedback.sharePhotoHint')}</T></T>
          </Pressable>
          {send.isError && <Notice icon="alert-circle" tone="error" text={t('feedback.error')} />}
          <Button kind="secondary" label={t('feedback.send')} icon="send" loading={send.isPending} onPress={() => send.mutate()} />
        </>
      )}
    </Card>
  );
}
