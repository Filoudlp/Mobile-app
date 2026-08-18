import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useFocusEffect, useRouter } from "expo-router";
import { Image } from "expo-image";
import { useCallback, useState } from "react";
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { clearHistory, HistoryEntry, loadHistory } from "@/src/storage/history";
import { CATEGORIES, getModule } from "@/src/data/modules";
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

const HISTORY_EMPTY_IMAGE =
  "https://images.pexels.com/photos/8470057/pexels-photo-8470057.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

function formatDate(ts: number) {
  const d = new Date(ts);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} • ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function categoryName(id: string) {
  return CATEGORIES.find((c) => c.id === id)?.shortName ?? id.toUpperCase();
}

export default function HistoriqueScreen() {
  const router = useRouter();
  const [entries, setEntries] = useState<HistoryEntry[]>([]);

  useFocusEffect(
    useCallback(() => {
      let mounted = true;
      loadHistory().then((rows) => {
        if (mounted) setEntries(rows);
      });
      return () => {
        mounted = false;
      };
    }, []),
  );

  const handleClear = async () => {
    await clearHistory();
    setEntries([]);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="history-screen">
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>HISTORIQUE</Text>
          <Text style={styles.subtitle}>
            {entries.length} calcul{entries.length !== 1 ? "s" : ""} sauvegardé
            {entries.length !== 1 ? "s" : ""}
          </Text>
        </View>
        {entries.length > 0 && (
          <Pressable
            onPress={handleClear}
            style={({ pressed }) => [
              styles.clearBtn,
              pressed && { opacity: 0.7 },
            ]}
            testID="history-clear-button"
          >
            <MaterialCommunityIcons
              name="trash-can-outline"
              size={16}
              color={colors.error}
            />
            <Text style={styles.clearBtnText}>VIDER</Text>
          </Pressable>
        )}
      </View>

      {entries.length === 0 ? (
        <View style={styles.emptyWrap} testID="history-empty">
          <Image
            source={HISTORY_EMPTY_IMAGE}
            style={styles.emptyImage}
            contentFit="cover"
          />
          <View style={styles.emptyOverlay} />
          <View style={styles.emptyContent}>
            <MaterialCommunityIcons
              name="clipboard-text-outline"
              size={48}
              color={colors.brand}
            />
            <Text style={styles.emptyTitle}>Aucun calcul sauvegardé</Text>
            <Text style={styles.emptyDesc}>
              Effectuez un calcul pour l&apos;enregistrer ici.
            </Text>
          </View>
        </View>
      ) : (
        <FlatList
          contentContainerStyle={styles.list}
          data={entries}
          keyExtractor={(item) => item.id}
          showsVerticalScrollIndicator={false}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => router.push(`/module/${item.moduleId}`)}
              style={({ pressed }) => [
                styles.card,
                pressed && { backgroundColor: colors.surfaceTertiary },
              ]}
              testID={`history-item-${item.id}`}
            >
              <View style={styles.cardHeader}>
                <View style={styles.cardIconWrap}>
                  <MaterialCommunityIcons
                    name={
                      (getModule(item.moduleId)?.icon ??
                        "calculator-variant") as keyof typeof MaterialCommunityIcons.glyphMap
                    }
                    size={18}
                    color={colors.brand}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardCat}>
                    {categoryName(item.categoryId)}
                  </Text>
                  <Text style={styles.cardTitle}>{item.moduleName}</Text>
                </View>
                <Text style={styles.cardDate}>{formatDate(item.createdAt)}</Text>
              </View>
              <View style={styles.cardBody}>
                {item.results.slice(0, 3).map((r, i) => (
                  <View key={i} style={styles.resultRow}>
                    <Text style={styles.resultLabel}>{r.label}</Text>
                    <Text
                      style={[
                        styles.resultValue,
                        r.status === "ok" && { color: colors.success },
                        r.status === "warning" && { color: colors.warning },
                        r.status === "error" && { color: colors.error },
                      ]}
                    >
                      {r.value}
                      {r.unit ? ` ${r.unit}` : ""}
                    </Text>
                  </View>
                ))}
              </View>
            </Pressable>
          )}
        />
      )}
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
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.surface,
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
  clearBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderColor: colors.error,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.sm,
  },
  clearBtnText: {
    color: colors.error,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1,
    fontFamily: fonts.text,
  },
  list: { padding: spacing.lg, paddingBottom: spacing.xl },
  card: {
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  cardIconWrap: {
    width: 32,
    height: 32,
    borderRadius: radius.sm,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  cardCat: {
    fontSize: 10,
    color: colors.brandSecondary,
    letterSpacing: 1.5,
    fontWeight: "700",
    fontFamily: fonts.text,
  },
  cardTitle: {
    color: colors.onSurface,
    fontSize: fontSize.lg,
    fontWeight: "600",
    fontFamily: fonts.text,
    marginTop: 2,
  },
  cardDate: {
    color: colors.onSurfaceTertiary,
    fontSize: 10,
    fontFamily: fonts.mono,
  },
  cardBody: { paddingTop: spacing.sm, gap: 4 },
  resultRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  resultLabel: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
  },
  resultValue: {
    color: colors.onSurface,
    fontSize: fontSize.base,
    fontWeight: "600",
    fontFamily: fonts.mono,
  },
  emptyWrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    margin: spacing.lg,
    borderRadius: radius.md,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.border,
  },
  emptyImage: { ...StyleSheet.absoluteFillObject },
  emptyOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(17,19,21,0.78)",
  },
  emptyContent: {
    alignItems: "center",
    padding: spacing.xl,
    gap: spacing.sm,
  },
  emptyTitle: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 20,
    fontWeight: "700",
    letterSpacing: 1,
    marginTop: spacing.sm,
  },
  emptyDesc: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    textAlign: "center",
    fontFamily: fonts.text,
  },
});
