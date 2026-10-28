import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import i18n, { resolveLanguage } from '../i18n';
import { useSettings } from '../store/settings';
import { useTheme } from '../theme/useTheme';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5 * 60 * 1000 } },
});

function LanguageSync() {
  const language = useSettings((s) => s.language);
  useEffect(() => {
    i18n.changeLanguage(resolveLanguage(language));
  }, [language]);
  return null;
}

function RootStack() {
  const { t } = useTranslation();
  const { colors, type } = useTheme();
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.background },
        headerShadowVisible: false,
        headerTintColor: colors.primary,
        headerTitleStyle: { fontSize: type.heading.fontSize, fontWeight: type.heading.fontWeight, color: colors.text },
        headerBackButtonDisplayMode: 'minimal',
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="review" options={{ title: t('review.title') }} />
      <Stack.Screen name="result" options={{ title: t('result.title') }} />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <LanguageSync />
          <StatusBar style="dark" />
          <RootStack />
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
