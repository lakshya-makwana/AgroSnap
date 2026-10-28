import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Switch, View } from 'react-native';

import { Card, Chip, List, Row, Screen, SectionLabel, T } from '../../components/ui';
import { LANGUAGES } from '../../i18n';
import { api } from '../../services/api';
import { useSettings } from '../../store/settings';
import { spacing } from '../../theme/tokens';
import { useTheme } from '../../theme/useTheme';

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  const { colors } = useTheme();
  return (
    <View style={{ minHeight: 56, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.md }}>
      <View style={{ flex: 1 }}><T>{label}</T></View>
      <Switch accessibilityLabel={label} value={value} onValueChange={onChange}
        trackColor={{ true: colors.primary, false: colors.surfaceMuted }} thumbColor="#FFFFFF" ios_backgroundColor={colors.surfaceMuted} />
    </View>
  );
}

export default function Profile() {
  const { t, i18n } = useTranslation();
  const s = useSettings();
  const info = useQuery({ queryKey: ['model-info'], queryFn: () => api.modelInfo(i18n.language) });

  return (
    <Screen>
      <SectionLabel>{t('profile.language')}</SectionLabel>
      <Card>
        <Row>
          {LANGUAGES.map((l) => (
            <Chip key={l.code} label={l.label} selected={i18n.language === l.code} onPress={() => s.setLanguage(l.code)} />
          ))}
        </Row>
      </Card>

      <SectionLabel>{t('profile.display')}</SectionLabel>
      <Card flush>
        <List>
          <Toggle label={t('profile.highContrast')} value={s.highContrast} onChange={s.setHighContrast} />
          <Toggle label={t('profile.largeText')} value={s.largeText} onChange={s.setLargeText} />
        </List>
      </Card>

      <SectionLabel>{t('profile.about')}</SectionLabel>
      <Card>
        <T>{t('profile.aboutBody')}</T>
        {info.data ? (
          <View style={{ gap: 2 }}>
            <T v="caption" muted>{t('profile.modelVersion', { version: info.data.model_version })}</T>
            {info.data.compression && (
              <T v="caption" muted>{t('profile.modelSize', {
                size: info.data.compression.size_MB.toFixed(1), times: info.data.compression.compression_x.toFixed(1),
              })}</T>
            )}
          </View>
        ) : info.isError ? <T v="caption" muted>{t('profile.serverError')}</T> : null}
      </Card>
    </Screen>
  );
}
