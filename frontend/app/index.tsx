// Landing publique C-Lab — présentation du projet.
// Accessible sans compte ; redirige vers /app si une session existe déjà.

import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth/AuthContext";
import { AppMenu } from "@/src/components/AppMenu";
import { CATEGORIES, MODULES } from "@/src/data/modules";
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

const FEATURES = [
  {
    icon: "book-open-variant",
    title: "Eurocodes et normes SIA",
    text:
      "Chaque vérification cite son article — EN 1991, 1992, 1993, 1998 et SIA 261 à 263. Les formules sont affichées avec leurs valeurs substituées.",
  },
  {
    icon: "function-variant",
    title: "Note de calcul complète",
    text:
      "L'onglet Détail déroule toutes les étapes intermédiaires, prêtes à justifier. Export PDF et copie vers Word en un clic.",
  },
  {
    icon: "chart-bell-curve",
    title: "Graphiques interactifs",
    text:
      "Spectre de réponse sismique, diagramme d'interaction N-M : les courbes se mettent à jour pendant la saisie et se copient dans vos rapports.",
  },
  {
    icon: "compare-horizontal",
    title: "Deux référentiels côte à côte",
    text:
      "Basculez entre Eurocode et SIA sur le même élément : les coefficients partiels et les méthodes s'ajustent automatiquement.",
  },
];

export default function Landing() {
  const router = useRouter();
  const { user, ready } = useAuth();
  const { width } = useWindowDimensions();
  const isWide = width >= 900;

  const availableCats = CATEGORIES.filter((c) => c.available);
  const moduleCount = MODULES.length;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <AppMenu />
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* ---- Hero ---- */}
        <View style={styles.hero}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>EUROCODES • SIA</Text>
          </View>
          <Text style={[styles.h1, isWide && styles.h1Wide]}>
            La boîte à outils de l&apos;ingénieur structure
          </Text>
          <Text style={[styles.lead, isWide && { maxWidth: 660 }]}>
            C-Lab réunit vos vérifications courantes — acier, béton, neige,
            vent, séisme — dans une interface unique, avec la note de calcul
            justifiée qui va avec.
          </Text>

          <View style={styles.ctaRow}>
            <Pressable
              onPress={() => router.push(user ? "/app" : "/login")}
              style={({ pressed }) => [styles.ctaPrimary, pressed && { opacity: 0.85 }]}
              testID="cta-start"
            >
              <MaterialCommunityIcons
                name="arrow-right"
                size={18}
                color={colors.onBrandPrimary}
              />
              <Text style={styles.ctaPrimaryText}>
                {user ? "Ouvrir mes calculs" : "Commencer gratuitement"}
              </Text>
            </Pressable>
            <Pressable
              onPress={() => router.push("/about")}
              style={({ pressed }) => [styles.ctaGhost, pressed && { opacity: 0.7 }]}
            >
              <Text style={styles.ctaGhostText}>En savoir plus</Text>
            </Pressable>
          </View>

          {ready && !user && (
            <Text style={styles.freeNote}>
              5 calculs par jour offerts — sans carte bancaire.
            </Text>
          )}
        </View>

        {/* ---- Chiffres ---- */}
        <View style={[styles.statsRow, !isWide && { flexDirection: "column" }]}>
          {[
            { v: String(moduleCount), l: "modules de calcul" },
            { v: String(availableCats.length), l: "familles couvertes" },
            { v: "2", l: "référentiels (EC / SIA)" },
          ].map((s) => (
            <View key={s.l} style={styles.statCard}>
              <Text style={styles.statValue}>{s.v}</Text>
              <Text style={styles.statLabel}>{s.l}</Text>
            </View>
          ))}
        </View>

        {/* ---- Fonctionnalités ---- */}
        <Text style={styles.sectionTitle}>CE QUE FAIT C-LAB</Text>
        <View style={[styles.featureGrid, isWide && styles.featureGridWide]}>
          {FEATURES.map((f) => (
            <View
              key={f.title}
              style={[styles.featureCard, isWide && styles.featureCardWide]}
            >
              <MaterialCommunityIcons
                name={f.icon as never}
                size={22}
                color={colors.brand}
              />
              <Text style={styles.featureTitle}>{f.title}</Text>
              <Text style={styles.featureText}>{f.text}</Text>
            </View>
          ))}
        </View>

        {/* ---- Modules disponibles ---- */}
        <Text style={styles.sectionTitle}>MODULES DISPONIBLES</Text>
        <View style={styles.moduleList}>
          {MODULES.map((m) => {
            const cat = CATEGORIES.find((c) => c.id === m.categoryId);
            return (
              <View key={m.id} style={styles.moduleRow}>
                <MaterialCommunityIcons
                  name={m.icon as never}
                  size={18}
                  color={colors.brandSecondary}
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.moduleName}>{m.name}</Text>
                  <Text style={styles.moduleDesc} numberOfLines={2}>
                    {m.description}
                  </Text>
                </View>
                <Text style={styles.moduleCat}>{cat?.shortName ?? ""}</Text>
              </View>
            );
          })}
        </View>

        {/* ---- Tarifs ---- */}
        <Text style={styles.sectionTitle}>TARIFS</Text>
        <View style={[styles.pricingRow, !isWide && { flexDirection: "column" }]}>
          <View style={styles.planCard}>
            <Text style={styles.planName}>Gratuit</Text>
            <Text style={styles.planPrice}>0 €</Text>
            <Text style={styles.planPeriod}>pour toujours</Text>
            <View style={styles.planSep} />
            {[
              "5 calculs par jour",
              "Tous les modules",
              "Historique de vos calculs",
            ].map((t) => (
              <View key={t} style={styles.planLine}>
                <MaterialCommunityIcons name="check" size={14} color={colors.success} />
                <Text style={styles.planLineText}>{t}</Text>
              </View>
            ))}
          </View>

          <View style={[styles.planCard, styles.planCardHighlight]}>
            <View style={styles.planTag}>
              <Text style={styles.planTagText}>ILLIMITÉ</Text>
            </View>
            <Text style={styles.planName}>Premium</Text>
            <Text style={styles.planPrice}>4,99 €</Text>
            <Text style={styles.planPeriod}>par mois, sans engagement</Text>
            <View style={styles.planSep} />
            {[
              "Calculs illimités",
              "Export PDF et Word",
              "Historique complet",
              "Nouveaux modules en priorité",
            ].map((t) => (
              <View key={t} style={styles.planLine}>
                <MaterialCommunityIcons name="check" size={14} color={colors.success} />
                <Text style={styles.planLineText}>{t}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* ---- Avertissement ---- */}
        <View style={styles.disclaimer}>
          <MaterialCommunityIcons
            name="alert-outline"
            size={16}
            color={colors.warning}
          />
          <Text style={styles.disclaimerText}>
            C-Lab est un outil d&apos;aide au dimensionnement. Les résultats
            doivent être vérifiés par un ingénieur qualifié : la responsabilité
            du dimensionnement reste celle de son auteur.
          </Text>
        </View>

        <Text style={styles.footer}>
          C-Lab — moteur de calcul Str-lib
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  scroll: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  hero: { paddingVertical: spacing.xl, alignItems: "flex-start" },
  badge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
    marginBottom: spacing.md,
  },
  badgeText: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 2,
    fontWeight: "700",
    fontFamily: fonts.mono,
  },
  h1: {
    color: colors.onSurface,
    fontSize: 30,
    fontWeight: "800",
    lineHeight: 38,
    marginBottom: spacing.md,
  },
  h1Wide: { fontSize: 42, lineHeight: 52, maxWidth: 720 },
  lead: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.base,
    lineHeight: 24,
    marginBottom: spacing.lg,
  },
  ctaRow: { flexDirection: "row", gap: spacing.sm, flexWrap: "wrap" },
  ctaPrimary: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.brand,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.sm,
  },
  ctaPrimaryText: {
    color: colors.onBrandPrimary,
    fontWeight: "800",
    fontSize: fontSize.sm,
    letterSpacing: 0.5,
  },
  ctaGhost: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  ctaGhostText: { color: colors.onSurface, fontWeight: "700", fontSize: fontSize.sm },
  freeNote: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.xs,
    marginTop: spacing.md,
  },
  statsRow: { flexDirection: "row", gap: spacing.md, marginBottom: spacing.xl },
  statCard: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.lg,
  },
  statValue: {
    color: colors.brand,
    fontSize: 28,
    fontWeight: "800",
    fontFamily: fonts.mono,
  },
  statLabel: { color: colors.onSurfaceTertiary, fontSize: fontSize.xs, marginTop: 4 },
  sectionTitle: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 2,
    fontWeight: "700",
    fontFamily: fonts.mono,
    marginBottom: spacing.md,
    marginTop: spacing.lg,
  },
  featureGrid: { gap: spacing.md },
  featureGridWide: { flexDirection: "row", flexWrap: "wrap" },
  featureCard: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  featureCardWide: { flexBasis: "48%", flexGrow: 1 },
  featureTitle: { color: colors.onSurface, fontSize: fontSize.base, fontWeight: "700" },
  featureText: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    lineHeight: 20,
  },
  moduleList: { gap: spacing.sm },
  moduleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.md,
  },
  moduleName: { color: colors.onSurface, fontSize: fontSize.sm, fontWeight: "700" },
  moduleDesc: { color: colors.onSurfaceTertiary, fontSize: fontSize.xs, marginTop: 2 },
  moduleCat: {
    color: colors.brandSecondary,
    fontSize: 9,
    letterSpacing: 1,
    fontWeight: "700",
    fontFamily: fonts.mono,
  },
  pricingRow: { flexDirection: "row", gap: spacing.md },
  planCard: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.lg,
  },
  planCardHighlight: { borderColor: colors.brand, borderWidth: 1.5 },
  planTag: {
    alignSelf: "flex-start",
    backgroundColor: colors.brand,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: radius.sm,
    marginBottom: spacing.sm,
  },
  planTagText: {
    color: colors.onBrandPrimary,
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 1,
    fontFamily: fonts.mono,
  },
  planName: { color: colors.onSurface, fontSize: fontSize.base, fontWeight: "700" },
  planPrice: {
    color: colors.onSurface,
    fontSize: 30,
    fontWeight: "800",
    marginTop: spacing.xs,
  },
  planPeriod: { color: colors.onSurfaceTertiary, fontSize: fontSize.xs },
  planSep: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: spacing.md,
  },
  planLine: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  planLineText: { color: colors.onSurfaceSecondary, fontSize: fontSize.sm, flex: 1 },
  disclaimer: {
    flexDirection: "row",
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.md,
    marginTop: spacing.xl,
  },
  disclaimerText: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.xs,
    lineHeight: 18,
    flex: 1,
  },
  footer: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.xs,
    textAlign: "center",
    marginTop: spacing.xl,
    fontFamily: fonts.mono,
  },
});
