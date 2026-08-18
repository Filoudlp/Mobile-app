import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import * as Linking from "expo-linking";
import { useLocalSearchParams, useRouter } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  AppState,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  createCheckoutSession,
  loadSubscription,
  PRICE_PER_MONTH,
  reconcileSubscription,
  refreshSubscription,
  SubscriptionState,
} from "@/src/subscription/subscription";
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

const FEATURES = [
  {
    icon: "infinity",
    title: "Calculs illimités",
    desc: "Plus de limite quotidienne — vérifiez autant d'éléments que nécessaire.",
  },
  {
    icon: "file-pdf-box",
    title: "Export PDF & Word",
    desc: "Générez vos notes de calcul prêtes à intégrer dans vos rapports.",
  },
  {
    icon: "history",
    title: "Historique complet",
    desc: "Retrouvez tous vos calculs sauvegardés sans limite.",
  },
  {
    icon: "star-outline",
    title: "Nouveaux modules en priorité",
    desc: "Béton armé, Bois, assemblages — dès qu'ils sont prêts.",
  },
];

// Return-URL scheme used by Stripe after checkout. We route back through
// the app's own web origin so the redirect works on iOS/Android/Web.
function buildReturnUrls(): { successUrl: string; cancelUrl: string } {
  if (Platform.OS === "web" && typeof window !== "undefined") {
    const origin = window.location.origin;
    return {
      successUrl: `${origin}/paywall?stripe_status=success&session_id={CHECKOUT_SESSION_ID}`,
      cancelUrl: `${origin}/paywall?stripe_status=cancel`,
    };
  }
  // Native — use expo-linking deep-link back into the app.
  const successUrl = Linking.createURL("paywall", {
    queryParams: {
      stripe_status: "success",
      session_id: "{CHECKOUT_SESSION_ID}",
    },
  });
  const cancelUrl = Linking.createURL("paywall", {
    queryParams: { stripe_status: "cancel" },
  });
  return { successUrl, cancelUrl };
}

export default function PaywallScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    stripe_status?: string;
    session_id?: string;
  }>();
  const [sub, setSub] = useState<SubscriptionState | null>(null);
  const [loading, setLoading] = useState(false);
  const [pollingBanner, setPollingBanner] = useState<null | "checking" | "success" | "cancel">(
    null,
  );
  const pollingRef = useRef<number | null>(null);

  const initialLoad = useCallback(async () => {
    const cached = await loadSubscription();
    setSub(cached);
    const fresh = await refreshSubscription();
    setSub(fresh);
  }, []);

  useEffect(() => {
    initialLoad();
  }, [initialLoad]);

  // Sync when the app comes back to foreground (user returned from Stripe).
  useEffect(() => {
    const listener = AppState.addEventListener("change", (state) => {
      if (state === "active") refreshSubscription().then(setSub).catch(() => {});
    });
    return () => listener.remove();
  }, []);

  // Handle Stripe redirect params (?stripe_status=success&session_id=...)
  useEffect(() => {
    const status = params.stripe_status;
    const sessionId = params.session_id;
    if (!status) return;
    if (status === "cancel") {
      setPollingBanner("cancel");
      return;
    }
    if (status === "success") {
      setPollingBanner("checking");
      const startedAt = Date.now();
      const poll = async () => {
        // Try reconcile first (Stripe API call), then plain status refresh.
        let state: SubscriptionState;
        if (sessionId && sessionId !== "{CHECKOUT_SESSION_ID}") {
          state = await reconcileSubscription(sessionId);
        } else {
          state = await refreshSubscription();
        }
        setSub(state);
        if (state.active) {
          setPollingBanner("success");
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
          return;
        }
        // Keep polling for ~30s while the webhook lands.
        if (Date.now() - startedAt < 30_000) {
          pollingRef.current = setTimeout(poll, 2_500) as unknown as number;
        } else {
          setPollingBanner(null);
        }
      };
      poll();
    }
  }, [params.stripe_status, params.session_id]);

  useEffect(() => () => {
    if (pollingRef.current) clearTimeout(pollingRef.current);
  }, []);

  const handleSubscribe = async () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setLoading(true);
    try {
      const { successUrl, cancelUrl } = buildReturnUrls();
      const { url } = await createCheckoutSession({ successUrl, cancelUrl });

      if (Platform.OS === "web") {
        // On web we do a full-page redirect so success_url actually
        // brings the user back inside the SPA.
        if (typeof window !== "undefined") window.location.href = url;
      } else {
        // Native — open in an in-app browser. When the user is done we
        // just refresh state; the deep-link redirect will re-open Paywall.
        await WebBrowser.openBrowserAsync(url, {
          dismissButtonStyle: "close",
          presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET,
        });
        const fresh = await refreshSubscription();
        setSub(fresh);
      }
    } catch (e: any) {
      Alert.alert(
        "Paiement indisponible",
        e?.message ?? "Impossible de démarrer le paiement Stripe.",
      );
    } finally {
      setLoading(false);
    }
  };

  const isActive = sub?.active === true;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="paywall-screen">
      <View style={styles.topBar}>
        <Pressable
          onPress={() => router.back()}
          hitSlop={12}
          style={({ pressed }) => [styles.close, pressed && { opacity: 0.6 }]}
          testID="paywall-close"
        >
          <MaterialCommunityIcons
            name="close"
            size={22}
            color={colors.onSurface}
          />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* Hero card */}
        <View style={styles.hero}>
          <LinearGradient
            colors={[colors.brand, "#B84600"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={StyleSheet.absoluteFillObject}
          />
          <View style={styles.heroContent}>
            <View style={styles.heroBadge}>
              <MaterialCommunityIcons
                name="star-four-points"
                size={12}
                color={colors.onBrandPrimary}
              />
              <Text style={styles.heroBadgeText}>PREMIUM</Text>
            </View>
            <Text style={styles.heroTitle}>Passez en illimité</Text>
            <Text style={styles.heroSubtitle}>
              Débloquez tous les calculs, exportez vos notes en PDF et Word.
            </Text>
            <View style={styles.priceRow}>
              <Text style={styles.priceValue}>{PRICE_PER_MONTH}</Text>
              <Text style={styles.priceHint}>Sans engagement</Text>
            </View>
          </View>
        </View>

        {/* Stripe status banner */}
        {pollingBanner === "checking" && (
          <View style={[styles.banner, styles.bannerInfo]}>
            <ActivityIndicator size="small" color={colors.brand} />
            <Text style={styles.bannerText}>
              Validation du paiement en cours…
            </Text>
          </View>
        )}
        {pollingBanner === "success" && (
          <View style={[styles.banner, styles.bannerSuccess]}>
            <MaterialCommunityIcons
              name="check-decagram"
              size={18}
              color={colors.success}
            />
            <Text style={styles.bannerText}>
              Abonnement Premium activé — merci !
            </Text>
          </View>
        )}
        {pollingBanner === "cancel" && (
          <View style={[styles.banner, styles.bannerWarning]}>
            <MaterialCommunityIcons
              name="alert-circle-outline"
              size={18}
              color={colors.warning}
            />
            <Text style={styles.bannerText}>
              Paiement annulé — vous pouvez réessayer.
            </Text>
          </View>
        )}

        {/* Features */}
        <Text style={styles.sectionLabel}>CE QUE VOUS DÉBLOQUEZ</Text>
        <View style={styles.featureList}>
          {FEATURES.map((f, i) => (
            <View
              key={f.title}
              style={[
                styles.featureRow,
                i !== FEATURES.length - 1 && styles.featureDivider,
              ]}
            >
              <View style={styles.featureIconWrap}>
                <MaterialCommunityIcons
                  name={f.icon as keyof typeof MaterialCommunityIcons.glyphMap}
                  size={20}
                  color={colors.brand}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.featureTitle}>{f.title}</Text>
                <Text style={styles.featureDesc}>{f.desc}</Text>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.finePrint}>
          <MaterialCommunityIcons
            name="information-outline"
            size={14}
            color={colors.onSurfaceTertiary}
          />
          <Text style={styles.finePrintText}>
            Abonnement récurrent facturé chaque mois via Stripe. Résiliation à
            tout moment — l&apos;accès reste valide jusqu&apos;à la fin de la
            période payée.
          </Text>
        </View>
      </ScrollView>

      {/* Sticky CTA */}
      <View style={styles.ctaBar}>
        {isActive ? (
          <View style={styles.activeBadge} testID="paywall-active-badge">
            <MaterialCommunityIcons
              name="check-decagram"
              size={20}
              color={colors.success}
            />
            <Text style={styles.activeBadgeText}>ABONNEMENT ACTIF</Text>
          </View>
        ) : (
          <Pressable
            onPress={handleSubscribe}
            disabled={loading}
            style={({ pressed }) => [
              styles.ctaButton,
              (pressed || loading) && { opacity: 0.7 },
            ]}
            testID="paywall-subscribe-button"
          >
            <MaterialCommunityIcons
              name={loading ? "progress-clock" : "crown"}
              size={20}
              color={colors.onBrandPrimary}
            />
            <Text style={styles.ctaText}>
              {loading ? "OUVERTURE STRIPE…" : `S'ABONNER — ${PRICE_PER_MONTH}`}
            </Text>
          </Pressable>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  topBar: { padding: spacing.md, alignItems: "flex-end" },
  close: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.sm,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  scroll: { paddingHorizontal: spacing.lg, paddingBottom: 120 },
  hero: {
    borderRadius: radius.lg,
    overflow: "hidden",
    minHeight: 190,
    marginBottom: spacing.xl,
  },
  heroContent: { padding: spacing.lg, flex: 1, justifyContent: "flex-end" },
  heroBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    alignSelf: "flex-start",
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    backgroundColor: "rgba(0,0,0,0.35)",
    borderRadius: radius.pill,
    marginBottom: spacing.sm,
  },
  heroBadgeText: {
    color: colors.onBrandPrimary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.5,
    fontFamily: fonts.text,
  },
  heroTitle: {
    color: colors.onBrandPrimary,
    fontSize: 30,
    fontWeight: "800",
    fontFamily: fonts.display,
    letterSpacing: 0.5,
  },
  heroSubtitle: {
    color: "rgba(255,255,255,0.9)",
    fontSize: fontSize.base,
    marginTop: 4,
    fontFamily: fonts.text,
  },
  priceRow: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  priceValue: {
    color: colors.onBrandPrimary,
    fontSize: 24,
    fontWeight: "800",
    fontFamily: fonts.display,
    letterSpacing: 0.5,
  },
  priceHint: {
    color: "rgba(255,255,255,0.85)",
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
  },
  banner: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.sm,
    borderLeftWidth: 3,
    marginBottom: spacing.md,
    backgroundColor: colors.surfaceSecondary,
  },
  bannerInfo: { borderLeftColor: colors.brand },
  bannerSuccess: { borderLeftColor: colors.success },
  bannerWarning: { borderLeftColor: colors.warning },
  bannerText: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
    flex: 1,
  },
  sectionLabel: {
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    letterSpacing: 2,
    fontWeight: "700",
    fontFamily: fonts.text,
    marginBottom: spacing.sm,
  },
  featureList: {
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
    marginBottom: spacing.lg,
  },
  featureRow: {
    flexDirection: "row",
    padding: spacing.md,
    gap: spacing.md,
  },
  featureDivider: {
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  featureIconWrap: {
    width: 36,
    height: 36,
    borderRadius: radius.sm,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  featureTitle: {
    color: colors.onSurface,
    fontSize: fontSize.base,
    fontWeight: "600",
    fontFamily: fonts.text,
  },
  featureDesc: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    marginTop: 2,
    fontFamily: fonts.text,
  },
  finePrint: {
    flexDirection: "row",
    gap: 6,
    alignItems: "flex-start",
    marginBottom: spacing.sm,
  },
  finePrintText: {
    flex: 1,
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    lineHeight: 15,
    fontFamily: fonts.text,
  },
  ctaBar: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    padding: spacing.lg,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  ctaButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.brand,
    paddingVertical: 16,
    borderRadius: radius.sm,
    gap: spacing.sm,
  },
  ctaText: {
    color: colors.onBrandPrimary,
    fontWeight: "800",
    letterSpacing: 1.5,
    fontSize: fontSize.base,
    fontFamily: fonts.text,
  },
  activeBadge: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.success,
    backgroundColor: colors.surfaceSecondary,
    gap: spacing.sm,
  },
  activeBadgeText: {
    color: colors.success,
    fontWeight: "800",
    letterSpacing: 1.5,
    fontSize: fontSize.base,
    fontFamily: fonts.text,
  },
});
