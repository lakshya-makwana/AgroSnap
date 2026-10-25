// Design tokens from docs/UI_UX.md §1. [A5] adds a high-contrast palette and a large-text scale.

export type Palette = {
  primary: string;
  primaryDark: string;
  primaryContainer: string;
  onPrimary: string;
  background: string;
  surface: string;
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
  primary: '#2E7D32',
  primaryDark: '#1B5E20',
  primaryContainer: '#E3F1E4',
  onPrimary: '#FFFFFF',
  background: '#FAF8F3',
  surface: '#FFFFFF',
  text: '#1C1F1A',
  textMuted: '#5B6157',
  border: '#E3E1DA',
  warning: '#B26A00',
  warningContainer: '#FFF3E0',
  error: '#B3261E',
  errorContainer: '#FDECEA',
  info: '#1565C0',
};

// For bright sunlight: pure white background, near-black text, darker accents, heavier borders.
export const highContrastPalette: Palette = {
  primary: '#1B5E20',
  primaryDark: '#0D3B12',
  primaryContainer: '#C8E6C9',
  onPrimary: '#FFFFFF',
  background: '#FFFFFF',
  surface: '#FFFFFF',
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
export const radius = { card: 16, button: 12 } as const;

const baseType = {
  display: { fontSize: 28, lineHeight: 34, fontWeight: '700' as const },
  title: { fontSize: 22, lineHeight: 28, fontWeight: '600' as const },
  heading: { fontSize: 18, lineHeight: 24, fontWeight: '600' as const },
  body: { fontSize: 16, lineHeight: 24, fontWeight: '400' as const },
  label: { fontSize: 14, lineHeight: 20, fontWeight: '500' as const },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: '400' as const },
};
export type TypeStyle = { fontSize: number; lineHeight: number; fontWeight: '400' | '500' | '600' | '700' };
export type TypeScale = Record<keyof typeof baseType, TypeStyle>;

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
