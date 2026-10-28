import NetInfo from '@react-native-community/netinfo';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { Children, type ReactNode, useEffect, useState } from 'react';
import {
  ActivityIndicator, Pressable, type PressableProps, ScrollView, type StyleProp, StyleSheet, Text, View,
  type ViewStyle,
} from 'react-native';
import Animated, { useReducedMotion } from 'react-native-reanimated';
import { useTranslation } from 'react-i18next';
import { SafeAreaView } from 'react-native-safe-area-context';

import { duration, EASE_IN_OUT_CSS, EASE_OUT_CSS } from '../theme/motion';
import { radius, spacing, touch, type TypeVariant } from '../theme/tokens';
import { useTheme } from '../theme/useTheme';

export type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

export function useOnline(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(() => NetInfo.addEventListener((s) => setOnline(s.isConnected !== false)), []);
  return online;
}

export function Screen({ children, scroll = true }: { children: ReactNode; scroll?: boolean }) {
  const { colors } = useTheme();
  const online = useOnline();
  const body = scroll ? (
    <ScrollView contentContainerStyle={styles.content}>{children}</ScrollView>
  ) : (
    <View style={[styles.content, { flex: 1 }]}>{children}</View>
  );
  return (
    <SafeAreaView edges={['left', 'right']} style={{ flex: 1, backgroundColor: colors.background }}>
      {!online && <OfflineBanner />}
      {body}
    </SafeAreaView>
  );
}

export function T({ v = 'body', muted, color, children, center, upper }: {
  v?: TypeVariant; muted?: boolean; color?: string; children: ReactNode; center?: boolean; upper?: boolean;
}) {
  const { colors, type } = useTheme();
  const { i18n } = useTranslation();
  // Tracking is tuned for Latin text; Devanagari conjuncts must not be squeezed or spread.
  const tracking = i18n.language === 'hi' ? { letterSpacing: 0 } : null;
  return (
    <Text style={[type[v], tracking, { color: color ?? (muted ? colors.textMuted : colors.text) },
      center && { textAlign: 'center' }, upper && { textTransform: 'uppercase' }]}>
      {children}
    </Text>
  );
}

/** Small uppercase label above a group, the way settings and system apps title sections. */
export function SectionLabel({ children }: { children: ReactNode }) {
  return <View style={{ paddingHorizontal: spacing.xs, marginBottom: -spacing.sm }}><T v="overline" muted upper>{children}</T></View>;
}

/** Any pressable surface: scales to 0.97 on press-in over 120ms (strong ease-out), back on release.
 *  Feedback starts on press-in, the action fires on press-out. Off when the system reduces motion. */
export function Pressy({ children, style, containerStyle, scaleTo = 0.97, onPressIn, onPressOut, ...rest }:
  PressableProps & { style?: StyleProp<ViewStyle>; containerStyle?: StyleProp<ViewStyle>; scaleTo?: number; children: ReactNode }) {
  const [pressed, setPressed] = useState(false);
  const reduced = useReducedMotion();
  return (
    <Pressable
      {...rest}
      style={containerStyle}
      pressRetentionOffset={{ top: 16, left: 16, right: 16, bottom: 16 }}
      onPressIn={(e) => { setPressed(true); onPressIn?.(e); }}
      onPressOut={(e) => { setPressed(false); onPressOut?.(e); }}
    >
      <Animated.View style={[style, {
        transform: [{ scale: pressed && !reduced ? scaleTo : 1 }],
        transitionProperty: 'transform', transitionDuration: duration.press, transitionTimingFunction: EASE_OUT_CSS,
      }]}>
        {children}
      </Animated.View>
    </Pressable>
  );
}

export function Button({ label, onPress, kind = 'primary', icon, disabled, loading, style }: {
  label: string; onPress: () => void; kind?: 'primary' | 'secondary' | 'text'; icon?: IconName;
  disabled?: boolean; loading?: boolean; style?: ViewStyle;
}) {
  const { colors, type, highContrast } = useTheme();
  const fg = kind === 'primary' ? colors.onPrimary : colors.primary;
  const bg = kind === 'primary' ? colors.primary : kind === 'secondary' ? colors.primaryContainer : 'transparent';
  return (
    <Pressy
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!disabled || !!loading, busy: !!loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={[
        styles.button,
        {
          minHeight: kind === 'primary' ? touch.primary : touch.min,
          backgroundColor: bg,
          borderColor: colors.primary,
          borderWidth: kind === 'secondary' && highContrast ? 2 : 0,
          opacity: disabled ? 0.45 : 1,
        },
        kind === 'text' && { paddingHorizontal: spacing.sm },
        style,
      ]}
    >
      {loading ? <ActivityIndicator color={fg} /> : icon ? <MaterialCommunityIcons name={icon} size={20} color={fg} /> : null}
      <Text style={[type.heading, { color: fg }]}>{label}</Text>
    </Pressy>
  );
}

export function Card({ children, tone = 'surface', style, flush }: {
  children: ReactNode; tone?: 'surface' | 'primary' | 'warning' | 'error'; style?: ViewStyle; flush?: boolean;
}) {
  const { colors, elevated, highContrast } = useTheme();
  const bg = { surface: colors.surface, primary: colors.primaryContainer, warning: colors.warningContainer,
    error: colors.errorContainer }[tone];
  // Tinted cards sit flat on the page; only white surfaces are raised.
  const edge = tone === 'surface' ? elevated : highContrast ? { borderWidth: 2, borderColor: colors.border } : null;
  return <View style={[styles.card, flush && styles.flush, { backgroundColor: bg }, edge, style]}>{children}</View>;
}

export function Row({ children, gap = spacing.sm, style }: { children: ReactNode; gap?: number; style?: ViewStyle }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap, flexWrap: 'wrap' }, style]}>{children}</View>;
}

export function Icon({ name, color, size = 24 }: { name: IconName; color?: string; size?: number }) {
  const { colors } = useTheme();
  return <MaterialCommunityIcons name={name} size={size} color={color ?? colors.text} />;
}

/** An icon on a soft tinted disc, used for empty states and list leading icons. */
export function IconBadge({ name, size = 44, tone = 'primary' }: { name: IconName; size?: number; tone?: 'primary' | 'muted' }) {
  const { colors } = useTheme();
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2, alignItems: 'center', justifyContent: 'center',
      backgroundColor: tone === 'primary' ? colors.primaryContainer : colors.surfaceMuted }}>
      <MaterialCommunityIcons name={name} size={Math.round(size * 0.5)} color={tone === 'primary' ? colors.primary : colors.textMuted} />
    </View>
  );
}

/** Rows separated by hairlines inside one card. */
export function List({ children }: { children: ReactNode }) {
  const { colors, borderWidth } = useTheme();
  const items = Children.toArray(children).filter(Boolean);
  return (
    <View>
      {items.map((child, i) => (
        <View key={i} style={i > 0 ? { borderTopWidth: borderWidth, borderTopColor: colors.border } : undefined}>{child}</View>
      ))}
    </View>
  );
}

/** Numbered guidance list: reads as instructions, not as a wall of tick marks. */
export function Steps({ items }: { items: string[] }) {
  const { colors, type } = useTheme();
  return (
    <View style={{ gap: spacing.md }}>
      {items.map((text, i) => (
        <View key={i} style={{ flexDirection: 'row', gap: spacing.md, alignItems: 'flex-start' }}>
          <View style={[styles.stepNum, { backgroundColor: colors.primaryContainer }]}>
            <Text style={[type.caption, { color: colors.primary, fontWeight: '700' }]}>{i + 1}</Text>
          </View>
          <View style={{ flex: 1, paddingTop: 1 }}><T v="label">{text}</T></View>
        </View>
      ))}
    </View>
  );
}

export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const { colors, type, borderWidth } = useTheme();
  return (
    <Pressy
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      hitSlop={4}
      onPress={() => {
        if (!selected) Haptics.selectionAsync();
        onPress();
      }}
      style={[styles.chip, {
        backgroundColor: selected ? colors.primary : colors.surface,
        borderColor: selected ? colors.primary : colors.border, borderWidth,
      }]}
    >
      {selected && <MaterialCommunityIcons name="check" size={16} color={colors.onPrimary} />}
      <Text style={[type.label, { color: selected ? colors.onPrimary : colors.text }]}>{label}</Text>
    </Pressy>
  );
}

/** Two or three peers. The thumb slides between options in 200ms (ease-in-out: it moves on screen). */
export function Segmented<K extends string>({ options, value, onChange }: {
  options: { key: K; label: string; icon?: IconName }[]; value: K; onChange: (k: K) => void;
}) {
  const { colors, type, elevated, highContrast } = useTheme();
  const [width, setWidth] = useState(0);
  const index = Math.max(0, options.findIndex((o) => o.key === value));
  const segment = width ? (width - 8) / options.length : 0;
  return (
    <View
      accessibilityRole="tablist"
      onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
      style={[styles.segment, { backgroundColor: colors.surfaceMuted },
        highContrast && { borderWidth: 2, borderColor: colors.border }]}
    >
      {segment > 0 && (
        <Animated.View pointerEvents="none" style={[styles.thumb, elevated, {
          width: segment, backgroundColor: colors.surface,
          transform: [{ translateX: index * segment }],
          transitionProperty: 'transform', transitionDuration: duration.control, transitionTimingFunction: EASE_IN_OUT_CSS,
        }]} />
      )}
      {options.map((o) => {
        const selected = o.key === value;
        const fg = selected ? colors.primary : colors.textMuted;
        return (
          <Pressable
            key={o.key}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            onPress={() => {
              if (!selected) Haptics.selectionAsync();
              onChange(o.key);
            }}
            style={styles.segmentItem}
          >
            {o.icon && <MaterialCommunityIcons name={o.icon} size={20} color={fg} />}
            <Text style={[type.label, { color: fg, fontWeight: '600' }]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

/** Confidence as a short bar plus words. Static on purpose: it is information, not decoration. */
export function Meter({ value, color }: { value: number; color: string }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.meter, { backgroundColor: colors.surfaceMuted }]}>
      <View style={{ width: `${Math.max(4, Math.min(100, value * 100))}%`, height: '100%', borderRadius: 3, backgroundColor: color }} />
    </View>
  );
}

export function OfflineBanner() {
  const { colors } = useTheme();
  const { t } = useTranslation();
  return (
    <View style={[styles.banner, { backgroundColor: colors.warningContainer }]} accessibilityLiveRegion="polite">
      <Icon name="wifi-off" color={colors.warning} size={18} />
      <T v="label" color={colors.warning}>{t('common.offline')}</T>
    </View>
  );
}

export function Notice({ icon, text, tone = 'warning' }: { icon: IconName; text: string; tone?: 'warning' | 'error' | 'primary' }) {
  const { colors, highContrast } = useTheme();
  const fg = { warning: colors.warning, error: colors.error, primary: colors.primaryDark }[tone];
  const bg = { warning: colors.warningContainer, error: colors.errorContainer, primary: colors.primaryContainer }[tone];
  return (
    <View accessibilityRole={tone === 'error' ? 'alert' : undefined}
      style={[styles.notice, { backgroundColor: bg }, highContrast && { borderWidth: 2, borderColor: colors.border }]}>
      <View style={{ paddingTop: 1 }}><Icon name={icon} color={fg} size={20} /></View>
      <View style={{ flex: 1 }}><T v="label" color={fg}>{text}</T></View>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingBottom: spacing.xxl, gap: spacing.lg },
  button: { borderRadius: radius.button, paddingHorizontal: spacing.lg, flexDirection: 'row', alignItems: 'center',
    justifyContent: 'center', gap: spacing.sm },
  card: { borderRadius: radius.card, padding: spacing.lg, gap: spacing.md },
  flush: { paddingVertical: spacing.xs },
  chip: { minHeight: 40, paddingHorizontal: spacing.md + 2, borderRadius: radius.pill, flexDirection: 'row',
    alignItems: 'center', gap: spacing.xs },
  segment: { flexDirection: 'row', borderRadius: radius.button, padding: 4 },
  thumb: { position: 'absolute', top: 4, bottom: 4, left: 4, borderRadius: radius.control },
  segmentItem: { flex: 1, minHeight: touch.min, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: spacing.sm },
  stepNum: { width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  meter: { height: 6, borderRadius: 3, overflow: 'hidden', flex: 1 },
  banner: { flexDirection: 'row', gap: spacing.sm, paddingHorizontal: spacing.lg, paddingVertical: spacing.sm + 2,
    alignItems: 'center' },
  notice: { flexDirection: 'row', gap: spacing.md, padding: spacing.md + 2, borderRadius: radius.button,
    alignItems: 'flex-start' },
});
