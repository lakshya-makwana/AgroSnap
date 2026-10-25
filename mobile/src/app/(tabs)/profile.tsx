import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Pressable, View } from 'react-native';

import { Card, Chip, Icon, Row, Screen, T } from '../../components/ui';
import { LANGUAGES } from '../../i18n';
import { api } from '../../services/api';
import { useSettings } from '../../store/settings';
import { useTheme } from '../../theme/useTheme';

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  const { colors } = useTheme();
  return (
    <Pressable accessibilityRole="switch" accessibilityState={{ checked: value }} onPress={() => onChange(!value)}
      style={{ minHeight: 56, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
      <View style={{ flex: 1 }}><T>{label}</T></View>
      <Icon name={value ? 'toggle-switch' : 'toggle-switch-off-outline'} size={44} color={value ? colors.primary : colors.textMuted} />
    </Pressable>
  );
}

export default function Profile() {
  const { t, i18n } = useTranslation();
  const s = useSettings();
  const info = useQuery({ queryKey: ['model-info'], queryFn: () => api.modelInfo(i18n.language) });

  return (
    <Screen>
      <Card>
        <T v="heading">{t('profile.language')}</T>
        <Row>
          {LANGUAGES.map((l) => (
            <Chip key={l.code} label={l.label} selected={i18n.language === l.code} onPress={() => s.setLanguage(l.code)} />
          ))}
        </Row>
      </Card>
      <Card>
        <T v="heading">{t('profile.display')}</T>
        <Toggle label={t('profile.highContrast')} value={s.highContrast} onChange={s.setHighContrast} />
        <Toggle label={t('profile.largeText')} value={s.largeText} onChange={s.setLargeText} />
      </Card>
      <Card>
        <T v="heading">{t('profile.about')}</T>
        <T>{t('profile.aboutBody')}</T>
        {info.data ? (
          <>
            <T v="caption" muted>{t('profile.modelVersion', { version: info.data.model_version })}</T>
            {info.data.compression && (
              <T v="caption" muted>{t('profile.modelSize', {
                size: info.data.compression.size_MB.toFixed(1), times: info.data.compression.compression_x.toFixed(1),
              })}</T>
            )}
          </>
        ) : info.isError ? <T v="caption" muted>{t('profile.serverError')}</T> : null}
      </Card>
    </Screen>
  );
}
