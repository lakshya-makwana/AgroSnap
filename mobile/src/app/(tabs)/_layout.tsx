import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';

import { useTheme } from '../../theme/useTheme';

type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

const TABS: { name: string; key: string; icon: IconName }[] = [
  { name: 'index', key: 'tabs.home', icon: 'home-variant' },
  { name: 'scan', key: 'tabs.scan', icon: 'leaf' },
  { name: 'weather', key: 'tabs.weather', icon: 'weather-partly-cloudy' },
  { name: 'farm', key: 'tabs.farm', icon: 'sprout' },
  { name: 'profile', key: 'tabs.profile', icon: 'account-circle' },
];

export default function TabLayout() {
  const { t } = useTranslation();
  const { colors, type, borderWidth } = useTheme();
  return (
    <Tabs
      screenOptions={{
        animation: 'none', // UI_UX §9: tab switches are never animated
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border, borderTopWidth: borderWidth, height: 64 },
        tabBarLabelStyle: { fontSize: type.caption.fontSize, fontWeight: '600' },
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.text,
        headerTitleStyle: { fontSize: type.title.fontSize, fontWeight: type.title.fontWeight },
      }}
    >
      {TABS.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: t(tab.key),
            tabBarIcon: ({ color, size }) => <MaterialCommunityIcons name={tab.icon} color={color as string} size={size + 2} />,
          }}
        />
      ))}
    </Tabs>
  );
}
