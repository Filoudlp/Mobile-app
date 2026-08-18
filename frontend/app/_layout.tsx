import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { StatusBar } from "expo-status-bar";
import { View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";

import { AuthProvider } from "@/src/auth/AuthContext";
import { useIconFonts } from "@/src/hooks/use-icon-fonts";

// Keep the native splash visible from cold start until icon fonts register.
SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [loaded, error] = useIconFonts();

  useEffect(() => {
    if (loaded || error) {
      SplashScreen.hideAsync();
    }
  }, [loaded, error]);

  if (!loaded && !error) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: "#111315" }}>
      <StatusBar style="light" />
      <View style={{ flex: 1 }}>
        <AuthProvider>
          <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: "#111315" } }}>
            <Stack.Screen name="index" />
            <Stack.Screen name="login" />
            <Stack.Screen name="about" />
            <Stack.Screen name="profile" />
            <Stack.Screen name="app" />
            <Stack.Screen name="module/[id]" options={{ presentation: "card" }} />
            <Stack.Screen name="paywall" options={{ presentation: "modal" }} />
          </Stack>
        </AuthProvider>
      </View>
    </GestureHandlerRootView>
  );
}
