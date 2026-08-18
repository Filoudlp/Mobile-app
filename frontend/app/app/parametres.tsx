import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { PRICE_PER_MONTH } from "@/src/subscription/subscription";
import {
  FREE_DAILY_LIMIT,
  useEntitlement,
} from "@/src/subscription/useEntitlement";
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

const NORMES = [
  { icon: "book-open-variant", label: "Acier", value: "Eurocode 3 (EC3)" },
  { icon: "book-open-variant", label: "Béton armé", value: "Eurocode 2 (EC2)" },
  { icon: "book-open-variant", label: "Bois", value: "Eurocode 5 (EC5)" },
];

const ABOUT = [
  { icon: "tag-outline", label: "Version", value: "1.0.0" },
  {
    icon: "function-variant",
    label: "Moteur de calcul",
    value: "Str-lib (Python)",
  },
  { icon: "shield-check-outline", label: "Données", value: "Locales" },
];

export default function ParametresScreen() {
  const router = useRouter();
  const { state, togglePremiumMock } = useEntitlement();
  const isPremium = state.premium.active;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="settings-screen">
      <View style={styles.header}>
        <Text style={styles.title}>PARAMÈTRES</Text>
        <Text style={styles.subtitle}>Configuration et informations</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* Subscription block */}
        <Text style={styles.sectionLabel}>ABONNEMENT</Text>
        <Pressable
          onPress={() => router.push("/paywall")}
          style={({ pressed }) => [
            styles.subCard,
            isPremium && styles.subCardActive,
            pressed && { opacity: 0.85 },
          ]}
          testID="settings-subscription-card"
        >
          <View style={styles.subIconWrap}>
            <MaterialCommunityIcons
              name={isPremium ? "crown" : "star-outline"}
              size={22}
              color={isPremium ? colors.brand : colors.brandSecondary}
            />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.subTitle}>
              {isPremium ? "C-Lab Premium" : "Passer Premium"}
            </Text>
            <Text style={styles.subDesc}>
              {isPremium
                ? "Calculs illimités • Sans publicité"
                : `${state.remaining}/${FREE_DAILY_LIMIT} calculs restants aujourd'hui`}
            </Text>
          </View>
          {!isPremium && (
            <View style={styles.pricePill}>
              <Text style={styles.pricePillText}>{PRICE_PER_MONTH}</Text>
            </View>
          )}
          <MaterialCommunityIcons
            name="chevron-right"
            size={22}
            color={colors.onSurfaceTertiary}
          />
        </Pressable>

        {/* Dev toggle for testing paywall */}
        <View style={styles.devRow} testID="settings-dev-toggle-row">
          <MaterialCommunityIcons
            name="flask-outline"
            size={16}
            color={colors.warning}
          />
          <Text style={styles.devRowLabel}>Mode Premium (test)</Text>
          <Switch
            value={isPremium}
            onValueChange={togglePremiumMock}
            trackColor={{ false: colors.borderStrong, true: colors.brand }}
            thumbColor={colors.onSurface}
            testID="settings-premium-switch"
          />
        </View>
        <Text style={styles.devHint}>
          Bascule temporaire pour tester le paywall — retirée avant publication
          (RevenueCat prendra le relais).
        </Text>

        {/* Normes */}
        <Text style={[styles.sectionLabel, { marginTop: spacing.xl }]}>
          NORMES
        </Text>
        <View style={styles.card}>
          {NORMES.map((row, i) => (
            <View
              key={row.label}
              style={[
                styles.row,
                i !== NORMES.length - 1 && styles.rowDivider,
              ]}
            >
              <View style={styles.rowIconWrap}>
                <MaterialCommunityIcons
                  name={
                    row.icon as keyof typeof MaterialCommunityIcons.glyphMap
                  }
                  size={18}
                  color={colors.brand}
                />
              </View>
              <Text style={styles.rowLabel}>{row.label}</Text>
              <Text style={styles.rowValue}>{row.value}</Text>
            </View>
          ))}
        </View>

        {/* About */}
        <Text style={[styles.sectionLabel, { marginTop: spacing.xl }]}>
          À PROPOS
        </Text>
        <View style={styles.card}>
          {ABOUT.map((row, i) => (
            <View
              key={row.label}
              style={[
                styles.row,
                i !== ABOUT.length - 1 && styles.rowDivider,
              ]}
            >
              <View style={styles.rowIconWrap}>
                <MaterialCommunityIcons
                  name={
                    row.icon as keyof typeof MaterialCommunityIcons.glyphMap
                  }
                  size={18}
                  color={colors.brand}
                />
              </View>
              <Text style={styles.rowLabel}>{row.label}</Text>
              <Text style={styles.rowValue}>{row.value}</Text>
            </View>
          ))}
        </View>

        <View style={styles.disclaimer}>
          <MaterialCommunityIcons
            name="alert-circle-outline"
            size={16}
            color={colors.warning}
          />
          <Text style={styles.disclaimerText}>
            Les calculs Poutre & Poteau utilisent votre librairie Str-lib
            (EC3-1-1). Les autres modules affichent des valeurs indicatives.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  title: {
    fontFamily: fonts.display,
    fontSize: 22,
    fontWeight: "800",
    color: colors.onSurface,
    letterSpacing: 3,
  },
  subtitle: {
    fontFamily: fonts.text,
    fontSize: fontSize.sm,
    color: colors.onSurfaceTertiary,
    marginTop: 2,
  },
  scroll: { padding: spacing.lg, paddingBottom: spacing.xl },
  sectionLabel: {
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    letterSpacing: 2,
    fontWeight: "700",
    marginBottom: spacing.sm,
    fontFamily: fonts.text,
  },
  subCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
    marginBottom: spacing.sm,
  },
  subCardActive: {
    borderColor: colors.brand,
    backgroundColor: colors.brandTertiary,
  },
  subIconWrap: {
    width: 40,
    height: 40,
    borderRadius: radius.sm,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  subTitle: {
    color: colors.onSurface,
    fontSize: fontSize.base,
    fontWeight: "700",
    fontFamily: fonts.text,
  },
  subDesc: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
    marginTop: 2,
  },
  pricePill: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    backgroundColor: colors.brand,
    borderRadius: radius.pill,
  },
  pricePillText: {
    color: colors.onBrandPrimary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.5,
    fontFamily: fonts.text,
  },
  devRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.sm,
    borderLeftWidth: 3,
    borderLeftColor: colors.warning,
  },
  devRowLabel: {
    flex: 1,
    color: colors.onSurface,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
  },
  devHint: {
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    marginTop: 4,
    paddingHorizontal: spacing.sm,
    fontStyle: "italic",
    fontFamily: fonts.text,
  },
  card: {
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    gap: spacing.md,
  },
  rowDivider: { borderBottomWidth: 1, borderBottomColor: colors.divider },
  rowIconWrap: {
    width: 32,
    height: 32,
    borderRadius: radius.sm,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  rowLabel: {
    flex: 1,
    color: colors.onSurface,
    fontSize: fontSize.base,
    fontFamily: fonts.text,
  },
  rowValue: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    fontFamily: fonts.mono,
  },
  disclaimer: {
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.md,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderLeftWidth: 3,
    borderLeftColor: colors.warning,
    marginTop: spacing.lg,
  },
  disclaimerText: {
    flex: 1,
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    lineHeight: 18,
    fontFamily: fonts.text,
  },
});
