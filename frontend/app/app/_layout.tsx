import { Tabs } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { Platform } from "react-native";

import { colors, fonts } from "@/src/theme";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.onSurfaceTertiary,
        tabBarStyle: {
          backgroundColor: colors.surfaceSecondary,
          borderTopColor: colors.divider,
          borderTopWidth: 1,
          height: Platform.OS === "ios" ? 84 : 64,
          paddingTop: 6,
          paddingBottom: Platform.OS === "ios" ? 26 : 8,
        },
        tabBarLabelStyle: {
          fontFamily: fonts.text,
          fontSize: 11,
          letterSpacing: 0.5,
          textTransform: "uppercase",
          fontWeight: "600",
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Modules",
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons
              name="grid"
              color={color}
              size={size}
              // @ts-expect-error -- testID propagates to host view
              testID="tab-icon-modules"
            />
          ),
        }}
      />
      <Tabs.Screen
        name="historique"
        options={{
          title: "Historique",
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons
              name="history"
              color={color}
              size={size}
              // @ts-expect-error -- testID propagates to host view
              testID="tab-icon-historique"
            />
          ),
        }}
      />
      <Tabs.Screen
        name="parametres"
        options={{
          title: "Paramètres",
          tabBarIcon: ({ color, size }) => (
            <MaterialCommunityIcons
              name="cog-outline"
              color={color}
              size={size}
              // @ts-expect-error -- testID propagates to host view
              testID="tab-icon-parametres"
            />
          ),
        }}
      />
    </Tabs>
  );
}
