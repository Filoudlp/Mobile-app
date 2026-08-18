// Connexion / inscription C-Lab.
// Un seul écran, bascule entre les deux modes : c'est le même formulaire.

import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
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
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

type Mode = "login" | "register";

export default function Login() {
  const router = useRouter();
  const { signIn, signUp } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRegister = mode === "register";

  const submit = async () => {
    setError(null);
    if (isRegister && password !== confirm) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }
    setBusy(true);
    try {
      if (isRegister) await signUp(email, password);
      else await signIn(email, password);
      router.replace("/app");
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Impossible de joindre le serveur. Réessayez.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <AppMenu />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.card}>
            <Text style={styles.title}>
              {isRegister ? "Créer un compte" : "Connexion"}
            </Text>
            <Text style={styles.subtitle}>
              {isRegister
                ? "5 calculs par jour offerts, sans carte bancaire."
                : "Retrouvez vos calculs et votre historique."}
            </Text>

            <Text style={styles.label}>Adresse e-mail</Text>
            <TextInput
              value={email}
              onChangeText={setEmail}
              placeholder="vous@bureau-etudes.fr"
              placeholderTextColor={colors.onSurfaceTertiary}
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              style={styles.input}
              testID="input-email"
            />

            <Text style={styles.label}>Mot de passe</Text>
            <TextInput
              value={password}
              onChangeText={setPassword}
              placeholder="8 caractères minimum"
              placeholderTextColor={colors.onSurfaceTertiary}
              secureTextEntry
              autoComplete={isRegister ? "new-password" : "current-password"}
              style={styles.input}
              testID="input-password"
              onSubmitEditing={submit}
            />

            {isRegister && (
              <>
                <Text style={styles.label}>Confirmer le mot de passe</Text>
                <TextInput
                  value={confirm}
                  onChangeText={setConfirm}
                  placeholder="Retapez le mot de passe"
                  placeholderTextColor={colors.onSurfaceTertiary}
                  secureTextEntry
                  style={styles.input}
                  testID="input-confirm"
                  onSubmitEditing={submit}
                />
              </>
            )}

            {error && (
              <View style={styles.errorBox} testID="auth-error">
                <MaterialCommunityIcons
                  name="alert-circle-outline"
                  size={15}
                  color={colors.error}
                />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <Pressable
              onPress={submit}
              disabled={busy}
              style={({ pressed }) => [
                styles.submit,
                (pressed || busy) && { opacity: 0.75 },
              ]}
              testID="auth-submit"
            >
              {busy ? (
                <ActivityIndicator color={colors.onBrandPrimary} />
              ) : (
                <Text style={styles.submitText}>
                  {isRegister ? "CRÉER MON COMPTE" : "SE CONNECTER"}
                </Text>
              )}
            </Pressable>

            <Pressable
              onPress={() => {
                setMode(isRegister ? "login" : "register");
                setError(null);
              }}
              style={styles.switch}
              testID="auth-switch"
            >
              <Text style={styles.switchText}>
                {isRegister
                  ? "J'ai déjà un compte — se connecter"
                  : "Pas encore de compte ? En créer un"}
              </Text>
            </Pressable>
          </View>

          <Text style={styles.legal}>
            En créant un compte vous acceptez que vos calculs soient conservés
            pour alimenter votre historique. Aucune donnée n&apos;est cédée à un
            tiers.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  scroll: {
    padding: spacing.lg,
    alignItems: "center",
    paddingTop: spacing.xl,
  },
  card: {
    width: "100%",
    maxWidth: 440,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    padding: spacing.lg,
  },
  title: { color: colors.onSurface, fontSize: 22, fontWeight: "800" },
  subtitle: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    marginTop: 4,
    marginBottom: spacing.lg,
  },
  label: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.xs,
    marginBottom: 6,
    marginTop: spacing.sm,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    backgroundColor: colors.surface,
    color: colors.onSurface,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    fontSize: fontSize.sm,
  },
  errorBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginTop: spacing.md,
    padding: spacing.sm,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.error,
    backgroundColor: colors.surface,
  },
  errorText: { color: colors.error, fontSize: fontSize.xs, flex: 1 },
  submit: {
    marginTop: spacing.lg,
    backgroundColor: colors.brand,
    borderRadius: radius.sm,
    paddingVertical: spacing.md,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 46,
  },
  submitText: {
    color: colors.onBrandPrimary,
    fontWeight: "800",
    fontSize: fontSize.sm,
    letterSpacing: 1,
  },
  switch: { marginTop: spacing.md, alignItems: "center" },
  switchText: { color: colors.brandSecondary, fontSize: fontSize.xs },
  legal: {
    color: colors.onSurfaceTertiary,
    fontSize: 10,
    maxWidth: 440,
    textAlign: "center",
    marginTop: spacing.lg,
    lineHeight: 16,
    fontFamily: fonts.mono,
  },
});
