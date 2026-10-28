// Design tokens (docs/UI_UX.md §1). [A5] adds a high-contrast palette and a large-text scale.
// Standard mode separates surfaces with a hairline plus a soft shadow; high contrast keeps solid borders.
import { StyleSheet } from 'react-native';

export type Palette = {
  primary: string;
  primaryDark: string;
  primaryContainer: string;
  onPrimary: string;
  background: string;
  surface: string;
  surfaceMuted: string;
  text: string;
  textMuted: string;
  border: string;
  warning: string;
  warningContainer: string;
  error: string;
  errorContainer: string;
  info: string;
};

export const standardPalette: Palette = {
  primary: '#21532F',
  primaryDark: '#163D22',
  primaryContainer: '#E6EEE4',
  onPrimary: '#FFFFFF',
  background: '#F5F4EF',
  surface: '#FFFFFF',
  surfaceMuted: '#ECEBE4',
  text: '#151813',
  textMuted: '#676C62',
  border: 'rgba(21, 24, 19, 0.09)',
  warning: '#8F5600',
  warningContainer: '#FAF0DE',
  error: '#A3271E',
  errorContainer: '#FAE9E7',
  info: '#24569B',
};

// For bright sunlight: pure white background, near-black text, darker accents, heavier borders.
export const highContrastPalette: Palette = {
  primary: '#1B5E20',
  primaryDark: '#0D3B12',
  primaryContainer: '#C8E6C9',
  onPrimary: '#FFFFFF',
  background: '#FFFFFF',
  surface: '#FFFFFF',
  surfaceMuted: '#EDEDED',
  text: '#000000',
  textMuted: '#262626',
  border: '#000000',
  warning: '#7A4100',
  warningContainer: '#FFE0B2',
  error: '#8E0000',
  errorContainer: '#FFCDD2',
  info: '#0D47A1',
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const radius = { card: 20, button: 14, control: 12, pill: 999 } as const;
export const hairline = StyleSheet.hairlineWidth;

// One soft, low shadow. Elevation stays at 1 so Android doesn't draw a heavy outline.
export const shadow = {
  shadowColor: '#1B2316',
  shadowOpacity: 0.06,
  shadowRadius: 14,
  shadowOffset: { width: 0, height: 4 },
  elevation: 1,
} as const;

const baseType = {
  display: { fontSize: 30, lineHeight: 36, fontWeight: '700' as const, letterSpacing: -0.6 },
  title: { fontSize: 22, lineHeight: 28, fontWeight: '600' as const, letterSpacing: -0.3 },
  heading: { fontSize: 17, lineHeight: 22, fontWeight: '600' as const, letterSpacing: -0.2 },
  body: { fontSize: 16, lineHeight: 23, fontWeight: '400' as const, letterSpacing: 0 },
  label: { fontSize: 14, lineHeight: 20, fontWeight: '500' as const, letterSpacing: 0 },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: '400' as const, letterSpacing: 0 },
  overline: { fontSize: 12, lineHeight: 16, fontWeight: '600' as const, letterSpacing: 0.8 },
};
export type TypeStyle = {
  fontSize: number; lineHeight: number; fontWeight: '400' | '500' | '600' | '700'; letterSpacing: number;
};
export type TypeScale = Record<keyof typeof baseType, TypeStyle>;
export type TypeVariant = keyof typeof baseType;

export function typeScale(large: boolean): TypeScale {
  if (!large) return baseType as TypeScale;
  const k = 1.25;
  return Object.fromEntries(
    Object.entries(baseType).map(([key, t]) => [
      key, { ...t, fontSize: Math.round(t.fontSize * k), lineHeight: Math.round(t.lineHeight * k) },
    ]),
  ) as TypeScale;
}

export const touch = { min: 48, primary: 56, capture: 76 } as const;
