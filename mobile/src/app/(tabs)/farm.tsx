import { useTranslation } from 'react-i18next';
import { View } from 'react-native';

import { Card, IconBadge, Screen, T } from '../../components/ui';
import { spacing } from '../../theme/tokens';

// Phase 6 (farm CRUD) needs accounts from Phase 7; until then this is an explained empty state.
export default function Farm() {
  const { t } = useTranslation();
  return (
    <Screen>
      <Card>
        <View style={{ alignItems: 'center', gap: spacing.md, paddingVertical: spacing.xl, paddingHorizontal: spacing.md }}>
          <IconBadge name="sprout-outline" size={72} />
          <T center muted>{t('farm.empty')}</T>
        </View>
      </Card>
    </Screen>
  );
}
