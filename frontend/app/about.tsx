// À propos de C-Lab — périmètre, normes couvertes, limites d'usage.

import { MaterialCommunityIcons } from "@expo/vector-icons";
import React from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AppMenu } from "@/src/components/AppMenu";
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

/** Normes réellement implémentées, par famille. */
const NORMES: { famille: string; items: string[] }[] = [
  {
    famille: "Actions",
    items: [
      "EN 1991-1-3 + NF NA — charges de neige",
      "EN 1991-1-4 + NF NA — actions du vent",
      "SIA 261 — neige, vent, séisme (Suisse)",
    ],
  },
  {
    famille: "Béton armé",
    items: [
      "EN 1992-1-1 §5.8 — effets du second ordre",
      "Recommandations professionnelles FFB — méthode forfaitaire",
      "SIA 262 §4.3.7 — éléments comprimés",
    ],
  },
  {
    famille: "Construction métallique",
    items: [
      "EN 1993-1-1 — résistance de section et stabilité",
      "EN 1993-1-5 §5 — voilement par cisaillement",
      "SIA 263 — résistance, flambage, déversement",
    ],
  },
  {
    famille: "Séisme",
    items: [
      "EN 1998-1 §3.2 — spectres de réponse",
      "SIA 261 chap. 16 — action sismique",
    ],
  },
];

const LIMITES = [
  "Les sections de classe 4 (voilement local) ne sont pas traitées.",
  "Les assemblages (boulonnage, soudure) sont hors périmètre.",
  "Fatigue, incendie et calcul non linéaire ne sont pas couverts.",
  "Certaines formules SIA reconstruites depuis des équations non extractibles du PDF sont signalées « à confirmer » dans la note de calcul.",
];

export default function About() {
  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <AppMenu />
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.h1}>À propos de C-Lab</Text>
        <Text style={styles.lead}>
          C-Lab regroupe les vérifications structurales courantes dans une
          interface unique, avec la justification normative complète : chaque
          résultat affiche sa formule, ses valeurs substituées et l&apos;article
          dont il découle.
        </Text>

        <Text style={styles.section}>MOTEUR DE CALCUL</Text>
        <View style={styles.card}>
          <Text style={styles.cardText}>
            Les calculs sont exécutés par{" "}
            <Text style={styles.mono}>Str-lib</Text>, une bibliothèque Python
            organisée en couches : matériaux et sections, puis vérifications
            unitaires indépendantes, puis classes d&apos;éléments qui les
            composent. Chaque vérification est isolée et testable seule, ce qui
            permet de la relire ligne à ligne face au texte normatif.
          </Text>
        </View>

        <Text style={styles.section}>NORMES COUVERTES</Text>
        {NORMES.map((n) => (
          <View key={n.famille} style={styles.card}>
            <Text style={styles.famille}>{n.famille}</Text>
            {n.items.map((it) => (
              <View key={it} style={styles.line}>
                <MaterialCommunityIcons
                  name="check"
                  size={14}
                  color={colors.success}
                />
                <Text style={styles.lineText}>{it}</Text>
              </View>
            ))}
          </View>
        ))}

        <Text style={styles.section}>CE QUI N&apos;EST PAS COUVERT</Text>
        <View style={styles.card}>
          {LIMITES.map((l) => (
            <View key={l} style={styles.line}>
              <MaterialCommunityIcons
                name="minus"
                size={14}
                color={colors.onSurfaceTertiary}
              />
              <Text style={styles.lineText}>{l}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.section}>RESPONSABILITÉ</Text>
        <View style={[styles.card, styles.warnCard]}>
          <View style={styles.line}>
            <MaterialCommunityIcons
              name="alert-outline"
              size={16}
              color={colors.warning}
            />
            <Text style={styles.lineText}>
              C-Lab est un outil d&apos;aide au dimensionnement. Il ne remplace
              pas le jugement de l&apos;ingénieur : les hypothèses, les
              combinaisons d&apos;actions et les résultats doivent être vérifiés
              par une personne qualifiée. La responsabilité du dimensionnement
              reste entièrement celle de son auteur.
            </Text>
          </View>
        </View>

        <Text style={styles.footer}>C-Lab — moteur Str-lib</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  scroll: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  h1: {
    color: colors.onSurface,
    fontSize: 26,
    fontWeight: "800",
    marginTop: spacing.md,
  },
  lead: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    lineHeight: 22,
    marginTop: spacing.sm,
  },
  section: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 2,
    fontWeight: "700",
    fontFamily: fonts.mono,
    marginBottom: spacing.sm,
    marginTop: spacing.xl,
  },
  card: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.lg,
    marginBottom: spacing.sm,
  },
  warnCard: { borderColor: colors.warning },
  cardText: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    lineHeight: 21,
  },
  mono: { fontFamily: fonts.mono, color: colors.onSurface },
  famille: {
    color: colors.onSurface,
    fontSize: fontSize.sm,
    fontWeight: "700",
    marginBottom: spacing.sm,
  },
  line: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    marginBottom: 6,
  },
  lineText: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.xs,
    lineHeight: 19,
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
