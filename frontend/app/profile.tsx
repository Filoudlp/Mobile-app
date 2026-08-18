// Profil C-Lab — compte, quota du jour, gestion de l'abonnement.

import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ApiError, useAuth } from "@/src/auth/AuthContext";
import { AppMenu } from "@/src/components/AppMenu";
import { PRICE_PER_MONTH } from "@/src/subscription/subscription";
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

export default function Profile() {
  const router = useRouter();
  const { user, usage, ready, refresh, signOut, changePassword } = useAuth();

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [pwBusy, setPwBusy] = useState(false);
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);

  // Un visiteur non connecté n'a rien à faire ici.
  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!ready || !user) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <AppMenu />
        <View style={styles.center}>
          <ActivityIndicator color={colors.brand} />
        </View>
      </SafeAreaView>
    );
  }

  const submitPassword = async () => {
    setPwMsg(null);
    setPwBusy(true);
    try {
      await changePassword(current, next);
      setPwMsg({ ok: true, text: "Mot de passe modifié." });
      setCurrent("");
      setNext("");
    } catch (e) {
      setPwMsg({
        ok: false,
        text: e instanceof ApiError ? e.message : "Échec de la modification.",
      });
    } finally {
      setPwBusy(false);
    }
  };

  const isPremium = !!usage?.premium;
  const used = usage?.used ?? 0;
  const limit = usage?.limit ?? 5;
  const pct = isPremium ? 0 : Math.min((used / Math.max(limit, 1)) * 100, 100);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <AppMenu />
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* ---- Compte ---- */}
        <Text style={styles.section}>COMPTE</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Adresse e-mail</Text>
            <Text style={styles.rowValue}>{user.email}</Text>
          </View>
          <View style={styles.sep} />
          <View style={styles.row}>
            <Text style={styles.rowLabel}>Formule</Text>
            <View style={styles.planPill}>
              <MaterialCommunityIcons
                name={isPremium ? "infinity" : "account-outline"}
                size={13}
                color={isPremium ? colors.success : colors.onSurfaceSecondary}
              />
              <Text
                style={[
                  styles.planPillText,
                  isPremium && { color: colors.success },
                ]}
              >
                {isPremium ? "Premium — illimité" : "Gratuit"}
              </Text>
            </View>
          </View>
          {user.created_at && (
            <>
              <View style={styles.sep} />
              <View style={styles.row}>
                <Text style={styles.rowLabel}>Compte créé le</Text>
                <Text style={styles.rowValue}>
                  {new Date(user.created_at).toLocaleDateString("fr-FR")}
                </Text>
              </View>
            </>
          )}
        </View>

        {/* ---- Quota ---- */}
        <Text style={styles.section}>CONSOMMATION DU JOUR</Text>
        <View style={styles.card}>
          {isPremium ? (
            <View style={styles.unlimitedRow}>
              <MaterialCommunityIcons
                name="infinity"
                size={22}
                color={colors.success}
              />
              <Text style={styles.unlimitedText}>
                Calculs illimités — aucune restriction quotidienne.
              </Text>
            </View>
          ) : (
            <>
              <View style={styles.quotaHead}>
                <Text style={styles.quotaBig}>
                  {used} <Text style={styles.quotaSmall}>/ {limit}</Text>
                </Text>
                <Text style={styles.quotaNote}>
                  {(usage?.remaining ?? 0) > 0
                    ? `${usage?.remaining} calcul(s) restant(s) aujourd'hui`
                    : "Quota atteint — revient demain ou passez en illimité"}
                </Text>
              </View>
              <View style={styles.barTrack}>
                <View
                  style={[
                    styles.barFill,
                    {
                      width: `${pct}%`,
                      backgroundColor:
                        pct >= 100
                          ? colors.error
                          : pct >= 80
                            ? colors.warning
                            : colors.brand,
                    },
                  ]}
                />
              </View>
              <Text style={styles.quotaReset}>
                Le compteur est remis à zéro chaque jour (heure UTC).
              </Text>
            </>
          )}
        </View>

        {/* ---- Abonnement ---- */}
        <Text style={styles.section}>ABONNEMENT</Text>
        <View style={styles.card}>
          {isPremium ? (
            <>
              <Text style={styles.cardText}>
                Votre abonnement est actif. La gestion (moyen de paiement,
                résiliation) se fait depuis le portail de facturation.
              </Text>
              <Pressable
                onPress={() => router.push("/paywall")}
                style={({ pressed }) => [
                  styles.btnGhost,
                  pressed && { opacity: 0.7 },
                ]}
              >
                <MaterialCommunityIcons
                  name="credit-card-outline"
                  size={16}
                  color={colors.onSurface}
                />
                <Text style={styles.btnGhostText}>Gérer mon abonnement</Text>
              </Pressable>
            </>
          ) : (
            <>
              <Text style={styles.cardText}>
                Passez en illimité pour {PRICE_PER_MONTH} : plus de limite
                quotidienne, export PDF et Word, historique complet.
              </Text>
              <Pressable
                onPress={() => router.push("/paywall")}
                style={({ pressed }) => [
                  styles.btnPrimary,
                  pressed && { opacity: 0.85 },
                ]}
                testID="profile-upgrade"
              >
                <MaterialCommunityIcons
                  name="crown-outline"
                  size={16}
                  color={colors.onBrandPrimary}
                />
                <Text style={styles.btnPrimaryText}>PASSER EN ILLIMITÉ</Text>
              </Pressable>
            </>
          )}
        </View>

        {/* ---- Mot de passe ---- */}
        <Text style={styles.section}>SÉCURITÉ</Text>
        <View style={styles.card}>
          <Text style={styles.rowLabel}>Mot de passe actuel</Text>
          <TextInput
            value={current}
            onChangeText={setCurrent}
            secureTextEntry
            style={styles.input}
            placeholderTextColor={colors.onSurfaceTertiary}
            testID="pw-current"
          />
          <Text style={[styles.rowLabel, { marginTop: spacing.sm }]}>
            Nouveau mot de passe
          </Text>
          <TextInput
            value={next}
            onChangeText={setNext}
            secureTextEntry
            placeholder="8 caractères minimum"
            placeholderTextColor={colors.onSurfaceTertiary}
            style={styles.input}
            testID="pw-new"
          />
          {pwMsg && (
            <Text
              style={[
                styles.pwMsg,
                { color: pwMsg.ok ? colors.success : colors.error },
              ]}
            >
              {pwMsg.text}
            </Text>
          )}
          <Pressable
            onPress={submitPassword}
            disabled={pwBusy || !current || !next}
            style={({ pressed }) => [
              styles.btnGhost,
              (pressed || pwBusy || !current || !next) && { opacity: 0.5 },
            ]}
            testID="pw-submit"
          >
            <Text style={styles.btnGhostText}>
              {pwBusy ? "Modification…" : "Modifier le mot de passe"}
            </Text>
          </Pressable>
        </View>

        {/* ---- Déconnexion ---- */}
        <Pressable
          onPress={async () => {
            await signOut();
            router.replace("/");
          }}
          style={({ pressed }) => [styles.logout, pressed && { opacity: 0.7 }]}
          testID="profile-logout"
        >
          <MaterialCommunityIcons name="logout" size={16} color={colors.error} />
          <Text style={styles.logoutText}>Se déconnecter</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  section: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 2,
    fontWeight: "700",
    fontFamily: fonts.mono,
    marginBottom: spacing.sm,
    marginTop: spacing.lg,
  },
  card: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.lg,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  rowLabel: { color: colors.onSurfaceTertiary, fontSize: fontSize.xs },
  rowValue: { color: colors.onSurface, fontSize: fontSize.sm, fontWeight: "600" },
  sep: { height: 1, backgroundColor: colors.border, marginVertical: spacing.md },
  planPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  planPillText: {
    color: colors.onSurfaceSecondary,
    fontSize: 11,
    fontWeight: "700",
  },
  unlimitedRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  unlimitedText: { color: colors.onSurfaceSecondary, fontSize: fontSize.sm, flex: 1 },
  quotaHead: { marginBottom: spacing.md },
  quotaBig: {
    color: colors.onSurface,
    fontSize: 30,
    fontWeight: "800",
    fontFamily: fonts.mono,
  },
  quotaSmall: { color: colors.onSurfaceTertiary, fontSize: 18 },
  quotaNote: { color: colors.onSurfaceTertiary, fontSize: fontSize.xs, marginTop: 2 },
  barTrack: {
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.surfaceTertiary,
    overflow: "hidden",
  },
  barFill: { height: "100%", borderRadius: 4 },
  quotaReset: {
    color: colors.onSurfaceTertiary,
    fontSize: 10,
    marginTop: spacing.sm,
  },
  cardText: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    lineHeight: 20,
    marginBottom: spacing.md,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    backgroundColor: colors.surface,
    color: colors.onSurface,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
    fontSize: fontSize.sm,
    marginTop: 6,
  },
  pwMsg: { fontSize: fontSize.xs, marginTop: spacing.sm },
  btnPrimary: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    backgroundColor: colors.brand,
    borderRadius: radius.sm,
    paddingVertical: spacing.md,
  },
  btnPrimaryText: {
    color: colors.onBrandPrimary,
    fontWeight: "800",
    fontSize: fontSize.sm,
    letterSpacing: 1,
  },
  btnGhost: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingVertical: spacing.md,
    marginTop: spacing.md,
  },
  btnGhostText: { color: colors.onSurface, fontSize: fontSize.sm, fontWeight: "600" },
  logout: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.xl,
    paddingVertical: spacing.md,
  },
  logoutText: { color: colors.error, fontSize: fontSize.sm, fontWeight: "600" },
});
