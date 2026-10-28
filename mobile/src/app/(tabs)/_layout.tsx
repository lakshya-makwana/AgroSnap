import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTheme } from '../../theme/useTheme';

type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

// Outline when idle, filled when selected: the selected tab reads by weight, not just by colour.
const TABS: { name: string; key: string; icon: IconName; active: IconName }[] = [
  { name: 'index', key: 'tabs.home', icon: 'home-variant-outline', active: 'home-variant' },
  { name: 'scan', key: 'tabs.scan', icon: 'leaf', active: 'leaf' },
  { name: 'weather', key: 'tabs.weather', icon: 'weather-partly-cloudy', active: 'weather-partly-cloudy' },
  { name: 'farm', key: 'tabs.farm', icon: 'sprout-outline', active: 'sprout' },
  { name: 'profile', key: 'tabs.profile', icon: 'account-circle-outline', active: 'account-circle' },
];

export default function TabLayout() {
  const { t } = useTranslation();
  const { colors, type, borderWidth } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <Tabs
      screenOptions={{
        animation: 'none', // UI_UX §9: tab switches are never animated
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border, borderTopWidth: borderWidth,
          height: 66 + insets.bottom, paddingTop: 6, paddingBottom: insets.bottom + 10 },
        tabBarLabelStyle: { fontSize: type.caption.fontSize - 2, fontWeight: '600' },
        headerStyle: { backgroundColor: colors.background },
        headerShadowVisible: false,
        headerTintColor: colors.text,
        headerTitleAlign: 'left',
        headerTitleStyle: { fontSize: type.title.fontSize, fontWeight: '700', letterSpacing: -0.3 },
      }}
    >
      {TABS.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: t(tab.key),
            headerShown: tab.name !== 'index',
            tabBarIcon: ({ color, focused }) => (
              <MaterialCommunityIcons name={focused ? tab.active : tab.icon} color={color as string} size={24} />
            ),
          }}
        />
      ))}
    </Tabs>
  );
}
