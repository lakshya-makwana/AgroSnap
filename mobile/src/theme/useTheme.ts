import type { ViewStyle } from 'react-native';

import { useSettings } from '../store/settings';
import { hairline, highContrastPalette, shadow, standardPalette, typeScale } from './tokens';

export function useTheme() {
  const highContrast = useSettings((s) => s.highContrast);
  const largeText = useSettings((s) => s.largeText);
  const colors = highContrast ? highContrastPalette : standardPalette;
  // A raised surface: hairline + soft shadow normally, a solid 2px border in high contrast.
  const elevated: ViewStyle = highContrast
    ? { borderWidth: 2, borderColor: colors.border }
    : { borderWidth: hairline, borderColor: colors.border, ...shadow };
  return {
    colors,
    type: typeScale(largeText),
    borderWidth: highContrast ? 2 : hairline,
    elevated,
    highContrast,
  };
}
