import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { Card, Icon, Screen, T } from '../../components/ui';
import { useTheme } from '../../theme/useTheme';

// Phase 6 (farm CRUD) needs accounts from Phase 7; until then this is an explained empty state.
export default function Farm() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return (
    <Screen>
      <Card>
        <View style={{ alignItems: 'center', paddingVertical: 16 }}><Icon name="sprout" size={64} color={colors.primary} /></View>
        <T center>{t('farm.empty')}</T>
      </Card>
    </Screen>
  );
}
