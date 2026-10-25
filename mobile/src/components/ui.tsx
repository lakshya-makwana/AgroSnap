import NetInfo from '@react-native-community/netinfo';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { type ReactNode, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View, type ViewStyle } from 'react-native';
import { useTranslation } from 'react-i18next';
import { SafeAreaView } from 'react-native-safe-area-context';

import { radius, spacing, touch } from '../theme/tokens';
import { useTheme } from '../theme/useTheme';

type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

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

export function T({ v = 'body', muted, color, children, center }: {
  v?: 'display' | 'title' | 'heading' | 'body' | 'label' | 'caption'; muted?: boolean; color?: string;
  children: ReactNode; center?: boolean;
}) {
  const { colors, type } = useTheme();
  return (
    <Text style={[type[v], { color: color ?? (muted ? colors.textMuted : colors.text) }, center && { textAlign: 'center' }]}>
      {children}
    </Text>
  );
}

export function Button({ label, onPress, kind = 'primary', icon, disabled, loading, style }: {
  label: string; onPress: () => void; kind?: 'primary' | 'secondary' | 'text'; icon?: IconName;
  disabled?: boolean; loading?: boolean; style?: ViewStyle;
}) {
  const { colors, type, borderWidth } = useTheme();
  const fg = kind === 'primary' ? colors.onPrimary : colors.primary;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!disabled || !!loading }}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        {
          minHeight: kind === 'primary' ? touch.primary : touch.min,
          backgroundColor: kind === 'primary' ? (pressed ? colors.primaryDark : colors.primary) : 'transparent',
          borderColor: colors.primary,
          borderWidth: kind === 'secondary' ? borderWidth + 1 : 0,
          opacity: disabled ? 0.5 : 1,
          transform: [{ scale: pressed ? 0.97 : 1 }],
        },
        style,
      ]}
    >
      {loading ? <ActivityIndicator color={fg} /> : icon ? <MaterialCommunityIcons name={icon} size={24} color={fg} /> : null}
      <Text style={[type.heading, { color: fg }]}>{label}</Text>
    </Pressable>
  );
}

export function Card({ children, tone = 'surface', style }: {
  children: ReactNode; tone?: 'surface' | 'primary' | 'warning' | 'error'; style?: ViewStyle;
}) {
  const { colors, borderWidth } = useTheme();
  const bg = { surface: colors.surface, primary: colors.primaryContainer, warning: colors.warningContainer,
    error: colors.errorContainer }[tone];
  return <View style={[styles.card, { backgroundColor: bg, borderColor: colors.border, borderWidth }, style]}>{children}</View>;
}

export function Row({ children, gap = spacing.sm, style }: { children: ReactNode; gap?: number; style?: ViewStyle }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center', gap, flexWrap: 'wrap' }, style]}>{children}</View>;
}

export function Icon({ name, color, size = 24 }: { name: IconName; color?: string; size?: number }) {
  const { colors } = useTheme();
  return <MaterialCommunityIcons name={name} size={size} color={color ?? colors.text} />;
}

export function Chip({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  const { colors, type, borderWidth } = useTheme();
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.chip, {
        backgroundColor: selected ? colors.primary : colors.surface,
        borderColor: selected ? colors.primary : colors.border, borderWidth: borderWidth + (selected ? 0 : 0),
      }]}
    >
      {selected && <MaterialCommunityIcons name="check" size={18} color={colors.onPrimary} />}
      <Text style={[type.label, { color: selected ? colors.onPrimary : colors.text }]}>{label}</Text>
    </Pressable>
  );
}

export function OfflineBanner() {
  const { colors } = useTheme();
  const { t } = useTranslation();
  return (
    <View style={[styles.banner, { backgroundColor: colors.warningContainer }]} accessibilityLiveRegion="polite">
      <Icon name="wifi-off" color={colors.warning} />
      <T v="label" color={colors.warning}>{t('common.offline')}</T>
    </View>
  );
}

export function Notice({ icon, text, tone = 'warning' }: { icon: IconName; text: string; tone?: 'warning' | 'error' | 'primary' }) {
  const { colors } = useTheme();
  const fg = { warning: colors.warning, error: colors.error, primary: colors.primaryDark }[tone];
  return (
    <Card tone={tone}>
      <Row style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
        <Icon name={icon} color={fg} />
        <View style={{ flex: 1 }}><T v="label" color={fg}>{text}</T></View>
      </Row>
    </Card>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.lg },
  button: { borderRadius: radius.button, paddingHorizontal: spacing.lg, flexDirection: 'row', alignItems: 'center',
    justifyContent: 'center', gap: spacing.sm },
  card: { borderRadius: radius.card, padding: spacing.lg, gap: spacing.sm },
  chip: { minHeight: touch.min, paddingHorizontal: spacing.lg, borderRadius: 24, flexDirection: 'row',
    alignItems: 'center', gap: spacing.xs },
  banner: { flexDirection: 'row', gap: spacing.sm, padding: spacing.md, alignItems: 'center' },
});
