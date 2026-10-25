import { useSettings } from '../store/settings';
import { highContrastPalette, standardPalette, typeScale } from './tokens';

export function useTheme() {
  const highContrast = useSettings((s) => s.highContrast);
  const largeText = useSettings((s) => s.largeText);
  return {
    colors: highContrast ? highContrastPalette : standardPalette,
    type: typeScale(largeText),
    borderWidth: highContrast ? 2 : 1,
    highContrast,
  };
}
