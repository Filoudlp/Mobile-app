// En-tête C-Lab avec menu déroulant : connexion / déconnexion, profil,
// à propos, et raccourcis vers l'application.
//
// Le contenu du menu s'adapte à l'état de session — inutile d'afficher
// « Déconnexion » à un visiteur, ou « Connexion » à un utilisateur connecté.

import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useAuth } from "../auth/AuthContext";
import { colors, fonts, fontSize, radius, spacing } from "../theme";

type MenuItem = {
  key: string;
  label: string;
  icon: string;
  onPress: () => void;
  danger?: boolean;
};

export function AppMenu({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const { user, usage, signOut } = useAuth();
  const [open, setOpen] = useState(false);

  const go = (path: string) => {
    setOpen(false);
    router.push(path as never);
  };

  const items: MenuItem[] = user
    ? [
        {
          key: "modules",
          label: "Mes calculs",
          icon: "view-grid-outline",
          onPress: () => go("/app"),
        },
        {
          key: "profile",
          label: "Profil et abonnement",
          icon: "account-circle-outline",
          onPress: () => go("/profile"),
        },
        {
          key: "history",
          label: "Historique",
          icon: "history",
          onPress: () => go("/app/historique"),
        },
        {
          key: "about",
          label: "À propos",
          icon: "information-outline",
          onPress: () => go("/about"),
        },
        {
          key: "logout",
          label: "Déconnexion",
          icon: "logout",
          danger: true,
          onPress: async () => {
            setOpen(false);
            await signOut();
            router.replace("/");
          },
        },
      ]
    : [
        {
          key: "login",
          label: "Connexion",
          icon: "login",
          onPress: () => go("/login"),
        },
        {
          key: "about",
          label: "À propos",
          icon: "information-outline",
          onPress: () => go("/about"),
        },
      ];

  return (
    <>
      <View style={[styles.header, compact && styles.headerCompact]}>
        <Pressable
          onPress={() => router.push(user ? "/app" : "/")}
          style={styles.brandZone}
          testID="brand-home"
        >
          <View style={styles.logoMark}>
            <Text style={styles.logoMarkText}>C</Text>
          </View>
          <View>
            <Text style={styles.brand}>C-LAB</Text>
            <Text style={styles.brandSub}>Calculs structuraux</Text>
          </View>
        </Pressable>

        <View style={styles.headerRight}>
          {user && usage && (
            <View style={styles.quotaChip} testID="header-quota">
              <MaterialCommunityIcons
                name={usage.premium ? "infinity" : "lightning-bolt-outline"}
                size={13}
                color={usage.premium ? colors.success : colors.brandSecondary}
              />
              <Text style={styles.quotaChipText}>
                {usage.premium
                  ? "ILLIMITÉ"
                  : `${usage.remaining ?? 0}/${usage.limit ?? 5}`}
              </Text>
            </View>
          )}
          <Pressable
            onPress={() => {
              Haptics.selectionAsync();
              setOpen(true);
            }}
            style={({ pressed }) => [styles.menuBtn, pressed && { opacity: 0.7 }]}
            testID="app-menu-button"
            accessibilityRole="button"
            accessibilityLabel="Ouvrir le menu"
          >
            <MaterialCommunityIcons
              name="menu"
              size={20}
              color={colors.onSurface}
            />
          </Pressable>
        </View>
      </View>

      <Modal
        visible={open}
        transparent
        animationType="fade"
        onRequestClose={() => setOpen(false)}
      >
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <Pressable
            style={styles.sheet}
            onPress={(e) => e.stopPropagation()}
            testID="app-menu-sheet"
          >
            {user && (
              <View style={styles.sheetHeader}>
                <Text style={styles.sheetEmail} numberOfLines={1}>
                  {user.email}
                </Text>
                <Text style={styles.sheetPlan}>
                  {user.premium ? "Abonnement illimité" : "Compte gratuit"}
                </Text>
              </View>
            )}
            {items.map((it) => (
              <Pressable
                key={it.key}
                onPress={it.onPress}
                style={({ pressed }) => [
                  styles.item,
                  pressed && { backgroundColor: colors.surfaceTertiary },
                ]}
                testID={`menu-${it.key}`}
              >
                <MaterialCommunityIcons
                  name={it.icon as never}
                  size={18}
                  color={it.danger ? colors.error : colors.onSurfaceSecondary}
                />
                <Text
                  style={[styles.itemText, it.danger && { color: colors.error }]}
                >
                  {it.label}
                </Text>
              </Pressable>
            ))}
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  headerCompact: { paddingVertical: spacing.sm },
  brandZone: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  logoMark: {
    width: 30,
    height: 30,
    borderRadius: radius.sm,
    backgroundColor: colors.brand,
    alignItems: "center",
    justifyContent: "center",
  },
  logoMarkText: {
    color: colors.onBrandPrimary,
    fontWeight: "800",
    fontSize: 17,
    fontFamily: fonts.mono,
  },
  brand: {
    color: colors.onSurface,
    fontSize: 15,
    fontWeight: "800",
    letterSpacing: 2,
    fontFamily: fonts.mono,
  },
  brandSub: { color: colors.onSurfaceTertiary, fontSize: 10 },
  headerRight: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  quotaChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
  },
  quotaChipText: {
    color: colors.onSurfaceSecondary,
    fontSize: 10,
    fontWeight: "700",
    fontFamily: fonts.mono,
  },
  menuBtn: {
    width: 36,
    height: 36,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
    alignItems: "center",
    justifyContent: "center",
  },
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
    alignItems: "flex-end",
    paddingTop: 64,
    paddingRight: spacing.lg,
  },
  sheet: {
    minWidth: 240,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
    paddingVertical: spacing.xs,
    overflow: "hidden",
  },
  sheetHeader: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    marginBottom: spacing.xs,
  },
  sheetEmail: { color: colors.onSurface, fontSize: fontSize.sm, fontWeight: "700" },
  sheetPlan: { color: colors.onSurfaceTertiary, fontSize: 11, marginTop: 2 },
  item: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  itemText: { color: colors.onSurface, fontSize: fontSize.sm },
});
