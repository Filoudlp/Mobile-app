import { useRouter, useFocusEffect } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useCallback } from "react";
import {
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Haptics from "expo-haptics";

import {
  CATEGORIES,
  CATEGORY_IMAGES,
  Category,
  getCategoryModules,
  ModuleDef,
} from "@/src/data/modules";
import { useAuth } from "@/src/auth/AuthContext";
import { AppMenu } from "@/src/components/AppMenu";
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

export default function HomeScreen() {
  const router = useRouter();
  const { refresh } = useAuth();

  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [refresh]),
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="home-screen">
      <AppMenu />

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.sectionLabel}>MATÉRIAUX</Text>

        {CATEGORIES.map((cat) => (
          <CategoryBlock
            key={cat.id}
            category={cat}
            onModulePress={(m) => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
              router.push(`/module/${m.id}`);
            }}
          />
        ))}

        <View style={styles.footerNote}>
          <MaterialCommunityIcons
            name="information-outline"
            size={14}
            color={colors.onSurfaceTertiary}
          />
          <Text style={styles.footerNoteText}>
            Interface seule — les calculs seront connectés à votre librairie
            Python.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function CategoryBlock({
  category,
  onModulePress,
}: {
  category: Category;
  onModulePress: (m: ModuleDef) => void;
}) {
  const modules = getCategoryModules(category.id);
  return (
    <View style={styles.categoryBlock} testID={`category-${category.id}`}>
      <View style={styles.heroCard}>
        <Image
          source={{ uri: CATEGORY_IMAGES[category.imageKey] }}
          style={styles.heroImage}
        />
        <LinearGradient
          colors={["rgba(17,19,21,0.1)", "rgba(17,19,21,0.55)", "rgba(17,19,21,0.95)"]}
          locations={[0, 0.55, 1]}
          style={styles.heroOverlay}
        />
        <View style={styles.heroContent}>
          <View style={styles.heroTopRow}>
            <Text style={styles.heroEyebrow}>CATÉGORIE</Text>
            {!category.available && (
              <View style={styles.soonChip}>
                <Text style={styles.soonChipText}>BIENTÔT</Text>
              </View>
            )}
          </View>
          <Text style={styles.heroTitle}>{category.shortName}</Text>
          <Text style={styles.heroMeta}>
            {modules.length > 0
              ? `${modules.length} module${modules.length > 1 ? "s" : ""} disponible${modules.length > 1 ? "s" : ""}`
              : "Modules à venir"}
          </Text>
        </View>
      </View>

      {modules.length > 0 ? (
        <View style={styles.moduleList}>
          {modules.map((m, idx) => (
            <Pressable
              key={m.id}
              onPress={() => onModulePress(m)}
              style={({ pressed }) => [
                styles.moduleRow,
                idx !== modules.length - 1 && styles.moduleRowDivider,
                pressed && styles.moduleRowPressed,
              ]}
              testID={`module-row-${m.id}`}
            >
              <View style={styles.moduleIconWrap}>
                <MaterialCommunityIcons
                  name={m.icon as keyof typeof MaterialCommunityIcons.glyphMap}
                  size={20}
                  color={colors.brand}
                />
              </View>
              <View style={styles.moduleTextWrap}>
                <Text style={styles.moduleName}>{m.name}</Text>
                <Text style={styles.moduleDesc} numberOfLines={1}>
                  {m.description}
                </Text>
              </View>
              <MaterialCommunityIcons
                name="chevron-right"
                size={22}
                color={colors.onSurfaceTertiary}
              />
            </Pressable>
          ))}
        </View>
      ) : (
        <View style={styles.placeholderList}>
          <Text style={styles.placeholderText}>
            Modules en cours de développement
          </Text>
        </View>
      )}
    </View>
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
  brandTag: {
    fontFamily: fonts.display,
    fontSize: 22,
    fontWeight: "800",
    color: colors.onSurface,
    letterSpacing: 3,
  },
  headerSubtitle: {
    fontFamily: fonts.text,
    fontSize: fontSize.sm,
    color: colors.onSurfaceTertiary,
    marginTop: 2,
    letterSpacing: 0.5,
  },
  headerBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
  },
  headerBadgePremium: {
    borderColor: colors.brand,
  },
  headerBadgePremium: {
    borderColor: colors.brand,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.brand,
  },
  headerBadgeText: {
    color: colors.onSurfaceSecondary,
    fontSize: 10,
    letterSpacing: 0.8,
    fontWeight: "700",
    fontFamily: fonts.text,
  },
  scroll: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
  },
  sectionLabel: {
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    letterSpacing: 2,
    fontWeight: "700",
    marginBottom: spacing.md,
    fontFamily: fonts.text,
  },
  categoryBlock: { marginBottom: spacing.xl },
  heroCard: {
    height: 150,
    borderRadius: radius.md,
    overflow: "hidden",
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
  },
  heroImage: { ...StyleSheet.absoluteFillObject, resizeMode: "cover" },
  heroOverlay: { ...StyleSheet.absoluteFillObject },
  heroContent: {
    flex: 1,
    justifyContent: "flex-end",
    padding: spacing.lg,
  },
  heroTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  heroEyebrow: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 2,
    fontWeight: "700",
    fontFamily: fonts.text,
  },
  heroTitle: {
    color: colors.onSurface,
    fontSize: 32,
    fontFamily: fonts.display,
    fontWeight: "800",
    letterSpacing: 1.5,
    marginTop: 4,
  },
  heroMeta: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    marginTop: 2,
    fontFamily: fonts.text,
  },
  soonChip: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    backgroundColor: colors.brandTertiary,
    borderRadius: radius.sm,
  },
  soonChipText: {
    color: colors.onBrandTertiary,
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 1,
    fontFamily: fonts.text,
  },
  moduleList: {
    marginTop: spacing.sm,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  moduleRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    gap: spacing.md,
  },
  moduleRowDivider: {
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  moduleRowPressed: { backgroundColor: colors.surfaceTertiary },
  moduleIconWrap: {
    width: 36,
    height: 36,
    borderRadius: radius.sm,
    backgroundColor: colors.brandTertiary,
    alignItems: "center",
    justifyContent: "center",
  },
  moduleTextWrap: { flex: 1 },
  moduleName: {
    color: colors.onSurface,
    fontSize: fontSize.lg,
    fontWeight: "600",
    fontFamily: fonts.text,
  },
  moduleDesc: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    marginTop: 2,
    fontFamily: fonts.text,
  },
  placeholderList: {
    marginTop: spacing.sm,
    paddingVertical: spacing.lg,
    alignItems: "center",
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: "dashed",
  },
  placeholderText: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    letterSpacing: 0.5,
    fontFamily: fonts.text,
  },
  footerNote: {
    marginTop: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: spacing.sm,
  },
  footerNoteText: {
    flex: 1,
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    fontFamily: fonts.text,
  },
});
