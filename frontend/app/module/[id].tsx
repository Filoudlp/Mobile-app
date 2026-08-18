import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useMemo, useState } from "react";
import {
  KeyboardAvoidingView,
  LayoutChangeEvent,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { BlueprintGrid } from "@/src/components/BlueprintGrid";
import { Schema } from "@/src/components/Schema";
import { InteractionChart } from "@/src/components/InteractionChart";
import { SpectrumChart } from "@/src/components/SpectrumChart";
import { getStoredToken, useAuth } from "@/src/auth/AuthContext";
import { FieldDef, getModule } from "@/src/data/modules";
import {
  copyDetailForWord,
  exportDetailPdf,
  ExportInputRow,
} from "@/src/export/detailExport";
import {
  copyDiagramImage,
  downloadDiagramImage,
} from "@/src/export/diagramExport";
import {
  HistoryEntry,
  HistoryResult,
  saveEntry,
} from "@/src/storage/history";
import { colors, fonts, fontSize, radius, spacing } from "@/src/theme";

type Tab = "donnees" | "schema" | "resultat" | "detail";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "donnees", label: "Données", icon: "form-textbox" },
  { id: "schema", label: "Schéma", icon: "vector-square" },
  { id: "resultat", label: "Résultat", icon: "chart-bar" },
  { id: "detail", label: "Détail", icon: "file-document-outline" },
];

type DetailRow = {
  label: string;
  unit?: string | null;
  value: string;
  formula?: string | null;
};
type DetailBlock = {
  title: string;
  rows: DetailRow[];
  subBlocks?: DetailBlock[];
};
type DetailPayload = { blocks: DetailBlock[] };

// Placeholder result generator (UI-only).
// Will be replaced by the user's Python library output.

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL ?? "";

/** Hauteur du cadre du diagramme [px] — partagée style / repli de mesure. */
const DIAGRAM_HEIGHT = 300;

export type DiagramPayload = {
  curve: { N: number; M: number }[];
  point: { N: number; M: number };
  labels?: { x: string; y: string };
};

type ComputeResponse = {
  results: HistoryResult[];
  detail: DetailPayload | null;
  diagram: DiagramPayload | null;
};

const num = (v: string | undefined, d = 0): number => {
  const n = parseFloat(v ?? "");
  return Number.isFinite(n) ? n : d;
};
const numOpt = (v: string | undefined): number | undefined => {
  const s = (v ?? "").trim();
  if (!s) return undefined;
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : undefined;
};

/** POSTe un payload vers l'API et normalise la réponse. */
async function postCalcul(
  path: string,
  payload: Record<string, unknown>,
): Promise<ComputeResponse> {
  const token = await getStoredToken();
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* réponse non JSON : on garde le message générique */
    }
    // 401 = session absente/expirée, 402 = quota épuisé. Les deux sont
    // gérés par l'appelant (redirection), pas affichés comme une erreur
    // de calcul.
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  const json = await res.json();
  return {
    results: json.results as HistoryResult[],
    detail: (json.detail ?? null) as DetailPayload | null,
    diagram: (json.diagram ?? null) as DiagramPayload | null,
  };
}

/** Calls the FastAPI backend (which delegates to Str-lib). */
async function computeViaBackend(
  moduleId: string,
  data: Record<string, string>,
): Promise<ComputeResponse> {
  if (moduleId === "neige-toiture") {
    const country = data.country || "FR";
    return postCalcul("/api/calcul/neige", {
      country,
      angle_deg: num(data.angle_deg, 20),
      exposure: data.exposure || "normal",
      Ct: num(data.Ct, 1.0),
      zone: country === "FR" ? data.zone || "A1" : undefined,
      altitude_m: numOpt(data.altitude_m),
      h0_m: country === "CH" ? numOpt(data.h0_m) : undefined,
    });
  }

  if (moduleId === "vent-facade") {
    const country = data.country || "FR";
    return postCalcul("/api/calcul/vent", {
      country,
      h_m: num(data.h_m, 9),
      b_m: num(data.b_m, 15),
      d_m: num(data.d_m, 25),
      terrain_category: data.terrain_category || "II",
      cscd: num(data.cscd, 1.0),
      region: country === "FR" ? data.region || "2" : undefined,
      cdir: num(data.cdir, 1.0),
      cseason: num(data.cseason, 1.0),
      qp0_kn_m2: country === "CH" ? numOpt(data.qp0_kn_m2) : undefined,
    });
  }

  if (moduleId === "seisme-spectre") {
    return postCalcul("/api/calcul/seisme", {
      country: data.country || "FR",
      zone: data.zone || "2",
      soil_class: data.soil_class || "C",
      q: num(data.q, 1.5),
      importance_class: data.importance_class || undefined,
      xi_percent: num(data.xi_percent, 5),
      t_point: numOpt(data.t_point),
    });
  }

  if (moduleId === "beton-poteau") {
    const shape = data.shape || "rect";
    return postCalcul("/api/calcul/beton/poteau", {
      norme: data.norme || "EC2",
      methode: data.methode || "courbure",
      shape,
      b_mm: num(data.b_mm, 300),
      h_mm: num(data.h_mm, 400),
      D_mm: num(data.D_mm, 400),
      l0_m: num(data.l0_m, 3.5),
      N_ed_kn: num(data.N_ed_kn),
      M0_top_knm: num(data.M0_top_knm),
      M0_bot_knm: num(data.M0_bot_knm),
      As_cm2: num(data.As_cm2),
      d_prime_mm: num(data.d_prime_mm, 50),
      concrete_class: data.concrete_class || "C25/30",
      rebar_grade: data.rebar_grade || "B500B",
      phi_ef: num(data.phi_ef, 2),
      c_curvature: num(data.c_curvature, 10),
      c0_stiffness: num(data.c0_stiffness, 8),
      show_diagram: data.show_diagram === "1",
    });
  }

  if (moduleId === "acier-poutre-flechie") {
    return postCalcul("/api/calcul/acier/poutre-flechie", {
      norme: data.norme || "EC3",
      profile: data.profile,
      grade: (data.grade ?? "").replace(" ", ""),
      N_ed_kn: num(data.N_ed),
      My_ed_knm: num(data.My_ed),
      Mz_ed_knm: num(data.Mz_ed),
      Vz_ed_kn: num(data.Vz_ed),
      Vy_ed_kn: num(data.Vy_ed),
      L_m: num(data.L_m, 6),
      Lcr_LT_m: numOpt(data.Lcr_LT_m),
      section_class: parseInt(data.section_class ?? "1", 10) || 1,
      profile_type: data.profile_type || "rolled",
      a_stiffener_m: numOpt(data.a_stiffener_m),
      psi: num(data.psi, 1),
      C1: num(data.C1, 1),
      q_els_kn_m: numOpt(data.q_els),
      support: data.support || "simply_supported",
      limit_type: data.limit_type || "floor_general",
    });
  }

  if (moduleId !== "acier-poteau-comprime") {
    throw new Error("Module non branché à l'API");
  }
  const curveOpt = (v: string | undefined): string | undefined =>
    v && v !== "auto" ? v : undefined;

  const length_m = num(data.length_m, 3);
  const Ky = num(data.Ky, 1);
  const Kz = num(data.Kz, 1);
  return postCalcul("/api/calcul/acier/poteau-comprime", {
    norme: data.norme || "EC3",
    profile: data.profile,
    grade: (data.grade ?? "").replace(" ", ""),
    N_ed_kn: num(data.N_ed),
    My_ed_knm: num(data.My_ed),
    Mz_ed_knm: num(data.Mz_ed),
    Vz_ed_kn: num(data.Vz_ed),
    Vy_ed_kn: num(data.Vy_ed),
    // Derived from bar length + K coefficients
    Lcry_m: Ky * length_m,
    Lcrz_m: Kz * length_m,
    LcrLT_m: numOpt(data.LcrLT_m) ?? length_m,
    length_m,
    Ky,
    Kz,
    psi_y: num(data.psi_y, 1),
    psi_z: num(data.psi_z, 1),
    C1: num(data.C1, 1),
    Cmy: num(data.Cmy, 0.9),
    Cmz: num(data.Cmz, 0.9),
    section_class: parseInt(data.section_class ?? "1", 10) || 1,
    interaction_method: parseInt(data.interaction_method ?? "2", 10) || 2,
    gamma_m0: numOpt(data.gamma_m0),
    gamma_m1: numOpt(data.gamma_m1),
    curve_y_override: curveOpt(data.curve_y),
    curve_z_override: curveOpt(data.curve_z),
    curve_LT_override: curveOpt(data.curve_LT),
  });
}

export default function ModuleScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const mod = useMemo(() => (id ? getModule(id) : undefined), [id]);

  const [tab, setTab] = useState<Tab>("donnees");
  const [data, setData] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    mod?.fields.forEach((f) => (init[f.key] = f.defaultValue));
    return init;
  });
  const [results, setResults] = useState<HistoryResult[] | null>(null);
  const [detail, setDetail] = useState<DetailPayload | null>(null);
  const [diagram, setDiagram] = useState<DiagramPayload | null>(null);
  const [openSelect, setOpenSelect] = useState<string | null>(null);
  const [computing, setComputing] = useState(false);
  const [computeError, setComputeError] = useState<string | null>(null);
  const {
    user: authUser,
    usage,
    refresh: refreshAuth,
    noteCalculation,
  } = useAuth();
  // Le quota vient du serveur : sans session on ne peut pas calculer.
  const canCompute = !!authUser && (usage?.can_compute ?? true);
  const quotaLabel = !authUser
    ? "CONNEXION REQUISE"
    : usage?.premium
      ? "PREMIUM ILLIMITÉ"
      : `${usage?.remaining ?? 0}/${usage?.limit ?? 5} CALCULS GRATUITS AUJOURD'HUI`;

  const { width: winWidth } = useWindowDimensions();
  const isSplit = mod?.layout === "split";
  const isDesktopSplit = isSplit && winWidth >= 768;
  const visibleTabs = isSplit ? TABS.filter((t) => t.id !== "schema") : TABS;

  if (!mod) {
    return (
      <SafeAreaView style={styles.safe}>
        <Text style={styles.errorTxt}>Module introuvable</Text>
      </SafeAreaView>
    );
  }

  const handleCompute = async () => {
    // Sans compte, aucun calcul : le quota est rattaché à l'utilisateur.
    if (!authUser) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      router.push("/login");
      return;
    }
    // Garde-fou côté client sur le quota connu ; le serveur reste l'autorité
    // et renverra 402 si le compte est effectivement épuisé.
    if (usage && !usage.can_compute) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      router.push("/paywall");
      return;
    }
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    setComputing(true);
    setComputeError(null);
    let response: ComputeResponse;
    try {
      response = await computeViaBackend(mod.id, data);
    } catch (e) {
      const status = (e as { status?: number })?.status;
      setComputing(false);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      if (status === 401) {
        await refreshAuth();
        router.push("/login");
        return;
      }
      if (status === 402) {
        await refreshAuth();
        router.push("/paywall");
        return;
      }
      setComputeError(e instanceof Error ? e.message : "Erreur de calcul");
      return;
    }
    setResults(response.results);
    setDetail(response.detail);
    setDiagram(response.diagram);
    const entry: HistoryEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      moduleId: mod.id,
      moduleName: mod.name,
      categoryId: mod.categoryId,
      createdAt: Date.now(),
      inputs: { ...data },
      results: response.results,
    };
    await saveEntry(entry);
    noteCalculation();
    setComputing(false);
    setTab("resultat");
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]} testID="module-screen">
      {/* Header */}
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={({ pressed }) => [
            styles.backBtn,
            pressed && { opacity: 0.6 },
          ]}
          testID="module-back-button"
          hitSlop={12}
        >
          <MaterialCommunityIcons
            name="chevron-left"
            size={26}
            color={colors.onSurface}
          />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerEyebrow}>
            {mod.categoryId === "acier"
              ? "ACIER • EC3"
              : mod.categoryId.toUpperCase()}
          </Text>
          <Text style={styles.headerTitle}>{mod.name}</Text>
        </View>
      </View>

      {/* Segmented control */}
      <View style={styles.segmented}>
        {visibleTabs.map((t) => {
          const active = tab === t.id;
          return (
            <Pressable
              key={t.id}
              onPress={() => {
                Haptics.selectionAsync();
                setTab(t.id);
              }}
              style={[styles.segment, active && styles.segmentActive]}
              testID={`segment-${t.id}`}
            >
              <MaterialCommunityIcons
                name={t.icon as keyof typeof MaterialCommunityIcons.glyphMap}
                size={16}
                color={active ? colors.onBrandPrimary : colors.onSurfaceSecondary}
              />
              <Text
                style={[
                  styles.segmentText,
                  active && styles.segmentTextActive,
                ]}
              >
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {computeError && (
        <View style={styles.errorBanner} testID="compute-error-banner">
          <MaterialCommunityIcons
            name="alert-circle"
            size={16}
            color={colors.error}
          />
          <Text style={styles.errorBannerText} numberOfLines={2}>
            {computeError}
          </Text>
        </View>
      )}

      {/* Content */}
      {tab === "donnees" && isSplit && (
        <View
          style={[
            styles.splitWrap,
            { flexDirection: isDesktopSplit ? "row" : "column-reverse" },
          ]}
          testID="split-layout"
        >
          <View style={styles.splitFormPane}>
            <DonneesTab
              fields={mod.fields}
              data={data}
              setData={setData}
              onOpenSelect={setOpenSelect}
              onCompute={handleCompute}
              computing={computing}
              canCompute={canCompute}
              quotaLabel={quotaLabel}
            />
          </View>
          <View
            style={
              isDesktopSplit
                ? styles.splitChartPaneDesktop
                : styles.splitChartPaneMobile
            }
            testID="split-chart-pane"
          >
            <SpectrumPreview data={data} />
          </View>
        </View>
      )}

      {tab === "donnees" && !isSplit && (
        <DonneesTab
          fields={mod.fields}
          data={data}
          setData={setData}
          onOpenSelect={setOpenSelect}
          onCompute={handleCompute}
          computing={computing}
          canCompute={canCompute}
          quotaLabel={quotaLabel}
        />
      )}

      {tab === "schema" && (
        <SchemaTab schemaType={mod.schemaType} data={data} />
      )}

      {tab === "resultat" && (
        <ResultatTab
          results={results}
          detail={detail}
          diagram={diagram}
          moduleName={mod.name}
          categoryLabel={
            mod.categoryId === "acier"
              ? "ACIER • EC3"
              : mod.categoryId.toUpperCase()
          }
          fields={mod.fields}
          data={data}
          onGo={() => setTab("donnees")}
        />
      )}

      {tab === "detail" && (
        <DetailTab
          detail={detail}
          onGo={() => setTab("donnees")}
          moduleName={mod.name}
          categoryLabel={
            mod.categoryId === "acier"
              ? "ACIER • EC3"
              : mod.categoryId.toUpperCase()
          }
          fields={mod.fields}
          data={data}
          results={results}
        />
      )}

      {/* Select modal */}
      <SelectSheet
        field={mod.fields.find((f) => f.key === openSelect) ?? null}
        currentValue={openSelect ? data[openSelect] : ""}
        filterGroup={
          (() => {
            const f = mod.fields.find((x) => x.key === openSelect);
            if (!f?.dependsOn) return undefined;
            return data[f.dependsOn];
          })()
        }
        onClose={() => setOpenSelect(null)}
        onPick={(value) => {
          if (openSelect) {
            setData((d) => {
              const next = { ...d, [openSelect]: value };
              // Cascade: if this field controls another field (via dependsOn),
              // reset the dependent field to the first option of the new group.
              const dependents = mod.fields.filter(
                (x) => x.dependsOn === openSelect,
              );
              for (const dep of dependents) {
                const firstOfGroup = dep.options?.find(
                  (o) => o.group === value,
                );
                if (firstOfGroup) next[dep.key] = firstOfGroup.value;
              }
              return next;
            });
          }
          setOpenSelect(null);
        }}
      />
    </SafeAreaView>
  );
}

/** Libellé affiché pour un select : le label de l'option courante plutôt
 * que sa valeur brute (ex. "Plancher courant — L/250" et non
 * "floor_general"). Retombe sur la valeur si aucune option ne correspond. */
function selectLabel(f: FieldDef, data: Record<string, string>): string {
  const value = data[f.key];
  if (!value) return "—";
  const group = f.dependsOn ? data[f.dependsOn] : undefined;
  const match =
    f.options?.find(
      (o) => o.value === value && (!group || !o.group || o.group === group),
    ) ?? f.options?.find((o) => o.value === value);
  return match?.label ?? value;
}

function DonneesTab({
  fields,
  data,
  setData,
  onOpenSelect,
  onCompute,
  computing,
  quotaLabel,
  canCompute,
}: {
  fields: FieldDef[];
  data: Record<string, string>;
  setData: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  onOpenSelect: (k: string) => void;
  onCompute: () => void;
  computing: boolean;
  quotaLabel: string;
  canCompute: boolean;
}) {
  const isVisible = (f: FieldDef) =>
    !f.showIf || data[f.showIf.key] === f.showIf.value;
  const visibleFields = fields.filter(isVisible);
  const baseFields = visibleFields.filter((f) => !f.advanced);
  const advancedFields = visibleFields.filter((f) => f.advanced);
  const [advOpen, setAdvOpen] = useState(false);

  const renderField = (f: FieldDef) => {
    // La case à cocher a sa propre disposition : libellé à droite de la
    // case, sur une seule ligne (pas de bloc label + champ).
    if (f.type === "checkbox") {
      const checked = data[f.key] === "1";
      return (
        <Pressable
          key={f.key}
          onPress={() => {
            Haptics.selectionAsync();
            setData((d) => ({ ...d, [f.key]: checked ? "" : "1" }));
          }}
          style={({ pressed }) => [
            styles.checkboxRow,
            pressed && { opacity: 0.7 },
          ]}
          testID={`checkbox-${f.key}`}
          accessibilityRole="checkbox"
          accessibilityState={{ checked }}
        >
          <View
            style={[styles.checkboxBox, checked && styles.checkboxBoxChecked]}
          >
            {checked && (
              <MaterialCommunityIcons
                name="check"
                size={15}
                color={colors.onBrandPrimary}
              />
            )}
          </View>
          <Text style={styles.checkboxLabel}>{f.label}</Text>
        </Pressable>
      );
    }
    return (
    <View key={f.key} style={styles.field} testID={`field-${f.key}`}>
      <View style={styles.fieldLabelRow}>
        <Text style={styles.fieldLabel}>{f.label}</Text>
        {f.unit && <Text style={styles.fieldUnit}>{f.unit}</Text>}
      </View>
      {f.type === "number" ? (
        <TextInput
          value={data[f.key]}
          onChangeText={(t) =>
            setData((d) => ({ ...d, [f.key]: t.replace(",", ".") }))
          }
          placeholder={f.placeholder}
          placeholderTextColor={colors.onSurfaceTertiary}
          keyboardType="decimal-pad"
          style={styles.input}
          testID={`input-${f.key}`}
        />
      ) : (
        <Pressable
          onPress={() => onOpenSelect(f.key)}
          style={styles.input}
          testID={`select-${f.key}`}
        >
          <Text style={styles.inputText}>{selectLabel(f, data)}</Text>
          <MaterialCommunityIcons
            name="chevron-down"
            size={18}
            color={colors.onSurfaceTertiary}
          />
        </Pressable>
      )}
    </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={80}
    >
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.formScroll}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.formCaption}>
          Saisir les paramètres d&apos;entrée de l&apos;élément à vérifier.
        </Text>

        {baseFields.map(renderField)}

        {advancedFields.length > 0 && (
          <View style={styles.advancedWrap} testID="advanced-section">
            <Pressable
              onPress={() => {
                Haptics.selectionAsync();
                setAdvOpen((v) => !v);
              }}
              style={({ pressed }) => [
                styles.advancedHeader,
                pressed && { opacity: 0.7 },
              ]}
              testID="advanced-toggle"
            >
              <MaterialCommunityIcons
                name="tune-variant"
                size={16}
                color={colors.brandSecondary}
              />
              <Text style={styles.advancedHeaderText}>PARAMÈTRES AVANCÉS</Text>
              <View style={styles.advancedBadge}>
                <Text style={styles.advancedBadgeText}>
                  {advancedFields.length}
                </Text>
              </View>
              <MaterialCommunityIcons
                name={advOpen ? "chevron-up" : "chevron-down"}
                size={20}
                color={colors.onSurfaceSecondary}
              />
            </Pressable>
            {advOpen && (
              <View style={styles.advancedBody} testID="advanced-body">
                {advancedFields.map(renderField)}
              </View>
            )}
          </View>
        )}
      </ScrollView>

      {/* Sticky CTA */}
      <View style={styles.ctaBar}>
        <Text style={styles.quotaLabel} testID="module-quota-label">
          {quotaLabel}
        </Text>
        <Pressable
          onPress={onCompute}
          disabled={computing}
          style={({ pressed }) => [
            styles.ctaButton,
            !canCompute && styles.ctaButtonPremium,
            (pressed || computing) && { opacity: 0.7 },
          ]}
          testID="calculer-button"
        >
          <MaterialCommunityIcons
            name={
              computing
                ? "progress-clock"
                : !canCompute
                  ? "crown"
                  : "calculator-variant"
            }
            size={20}
            color={colors.onBrandPrimary}
          />
          <Text style={styles.ctaText}>
            {computing
              ? "CALCUL EN COURS…"
              : !canCompute
                ? "PASSER PREMIUM"
                : "CALCULER"}
          </Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

function SchemaTab({
  schemaType,
  data,
}: {
  schemaType?: "beam" | "column" | "bolt" | "roof" | "wind" | "rc-column";
  data: Record<string, string>;
}) {
  const [size, setSize] = useState({ width: 0, height: 0 });
  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setSize({ width, height });
  };
  if (!schemaType) return null;
  return (
    <View style={styles.schemaWrap} onLayout={onLayout} testID="schema-canvas">
      {size.width > 0 && (
        <>
          <BlueprintGrid width={size.width} height={size.height} />
          <Schema
            type={schemaType}
            width={size.width}
            height={size.height}
            data={data}
          />
        </>
      )}
      <View style={styles.schemaCorner}>
        <Text style={styles.schemaCornerText}>BLUEPRINT • 1:50</Text>
      </View>
    </View>
  );
}

function SpectrumPreview({ data }: { data: Record<string, string> }) {
  const [size, setSize] = useState({ width: 0, height: 0 });
  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setSize({ width, height });
  };
  return (
    <View style={styles.spectrumWrap} onLayout={onLayout} testID="spectrum-canvas">
      {size.width > 0 && (
        <SpectrumChart width={size.width} height={size.height} data={data} />
      )}
    </View>
  );
}

function ResultatTab({
  results,
  detail,
  diagram,
  moduleName,
  categoryLabel,
  fields,
  data,
  onGo,
}: {
  results: HistoryResult[] | null;
  detail: DetailPayload | null;
  diagram: DiagramPayload | null;
  moduleName: string;
  categoryLabel: string;
  fields: FieldDef[];
  data: Record<string, string>;
  onGo: () => void;
}) {
  // La largeur est mesurée sur le conteneur lui-même (et non sur la
  // fenêtre) : le découpage suit la place réellement disponible pour les
  // résultats, ce qui reste correct si la zone est encadrée ou réduite.
  const [paneWidth, setPaneWidth] = useState(0);
  const onPaneLayout = (e: LayoutChangeEvent) =>
    setPaneWidth(e.nativeEvent.layout.width);
  const { width: winWidth } = useWindowDimensions();
  // Largeur utile = celle du conteneur, qui ne peut pas dépasser la
  // fenêtre. Le min protège d'une mesure devenue obsolète après un
  // rétrécissement (la fenêtre, elle, est toujours à jour) ; le repli sur
  // winWidth couvre le premier rendu, avant la première mesure.
  const effectiveWidth = paneWidth ? Math.min(paneWidth, winWidth) : winWidth;
  // Sur PC (≥ 900 px utiles) le diagramme se place à droite des résultats ;
  // en dessous il passe dessous, empilé.
  const isWide = effectiveWidth >= 900;

  if (!results) {
    return (
      <View style={styles.emptyResult} testID="result-empty">
        <MaterialCommunityIcons
          name="gauge"
          size={56}
          color={colors.onSurfaceTertiary}
        />
        <Text style={styles.emptyResultTitle}>Aucun résultat</Text>
        <Text style={styles.emptyResultDesc}>
          Lancez un calcul depuis l&apos;onglet Données.
        </Text>
        <Pressable
          onPress={onGo}
          style={styles.emptyResultBtn}
          testID="goto-donnees-button"
        >
          <Text style={styles.emptyResultBtnText}>ALLER AUX DONNÉES</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.resultScroll}
      showsVerticalScrollIndicator={false}
      testID="result-list"
    >
      <View style={styles.resultHeader}>
        <Text style={styles.resultEyebrow}>SORTIE DU MOTEUR DE CALCUL</Text>
        <Text style={styles.resultSubtitle}>
          Calculé via Str-lib — {categoryLabel}
        </Text>
      </View>

      <ExportBar
        moduleName={moduleName}
        categoryLabel={categoryLabel}
        fields={fields}
        data={data}
        results={results}
        detail={detail}
      />

      <View
        style={[
          styles.resultSplit,
          { flexDirection: isWide && diagram ? "row" : "column" },
        ]}
        onLayout={onPaneLayout}
      >
        <View style={isWide && diagram ? styles.resultSplitLeft : undefined}>
          {results.map((r, i) => {
            const color =
              r.status === "ok"
                ? colors.success
                : r.status === "warning"
                  ? colors.warning
                  : r.status === "error"
                    ? colors.error
                    : colors.onSurface;
            return (
              <View
                key={i}
                style={styles.metricRow}
                testID={`result-row-${i}`}
              >
                <Text style={styles.metricLabel}>{r.label}</Text>
                <View style={styles.metricValueWrap}>
                  <Text style={[styles.metricValue, { color }]}>{r.value}</Text>
                  {r.unit && <Text style={styles.metricUnit}>{r.unit}</Text>}
                </View>
              </View>
            );
          })}
        </View>
        {diagram && (
          <View style={isWide ? styles.resultSplitRight : undefined}>
            <DiagramPanel diagram={diagram} moduleName={moduleName} />
          </View>
        )}
      </View>

      <View style={styles.savedNote}>
        <MaterialCommunityIcons
          name="check-circle-outline"
          size={16}
          color={colors.success}
        />
        <Text style={styles.savedNoteText}>
          Calcul enregistré dans l&apos;historique
        </Text>
      </View>
    </ScrollView>
  );
}

/** Panneau du diagramme de capacité N-M (affiché si la case est cochée). */
function DiagramPanel({
  diagram,
  moduleName,
}: {
  diagram: DiagramPayload;
  moduleName: string;
}) {
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [copyState, setCopyState] = useState<"idle" | "done" | "fallback" | "error">(
    "idle",
  );
  const { width: winWidth } = useWindowDimensions();
  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setSize({ width, height });
  };
  // Le tracé a besoin d'une largeur. On prend la mesure du conteneur, et à
  // défaut une estimation depuis la fenêtre : sans ce repli, un onLayout
  // qui ne remonte pas laisserait un cadre vide au lieu du graphique.
  const chartW = size.width || Math.max(Math.min(winWidth - 64, 900), 280);
  const chartH = size.height || DIAGRAM_HEIGHT;

  const onCopy = async () => {
    Haptics.selectionAsync();
    const res = await copyDiagramImage("diagram-canvas", colors.surface);
    if (res.ok) {
      setCopyState("done");
    } else {
      // Presse-papiers image indisponible (navigateur ancien, permission
      // refusée, mobile) : on retombe sur un téléchargement PNG, que
      // l'utilisateur insère ensuite dans Word.
      const dl = await downloadDiagramImage(
        "diagram-canvas",
        `diagramme-${moduleName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.png`,
        colors.surface,
      );
      setCopyState(dl ? "fallback" : "error");
    }
    setTimeout(() => setCopyState("idle"), 2600);
  };

  const copyLabel =
    copyState === "done"
      ? "COPIÉ ✓"
      : copyState === "fallback"
        ? "PNG TÉLÉCHARGÉ"
        : copyState === "error"
          ? "ÉCHEC"
          : "COPIER L'IMAGE";

  return (
    <View style={styles.diagramWrap} testID="interaction-diagram">
      <View style={styles.diagramHeader}>
        <Text style={styles.diagramTitle}>DIAGRAMME DE CAPACITÉ N-M</Text>
        <Pressable
          onPress={onCopy}
          style={({ pressed }) => [
            styles.diagramCopyBtn,
            pressed && { opacity: 0.7 },
          ]}
          testID="diagram-copy-button"
        >
          <MaterialCommunityIcons
            name={copyState === "done" ? "check" : "content-copy"}
            size={13}
            color={colors.brandSecondary}
          />
          <Text style={styles.diagramCopyText}>{copyLabel}</Text>
        </Pressable>
      </View>
      <View
        style={styles.diagramCanvas}
        onLayout={onLayout}
        testID="diagram-canvas"
      >
        <InteractionChart width={chartW} height={chartH} data={diagram} />
      </View>
      <Text style={styles.diagramHint}>
        L&apos;image est copiée en PNG — collage direct dans Word.
      </Text>
    </View>
  );
}

/** Shared PDF / Word export toolbar — used by both the Résultat and Détail tabs. */
function ExportBar({
  moduleName,
  categoryLabel,
  fields,
  data,
  results,
  detail,
}: {
  moduleName: string;
  categoryLabel: string;
  fields: FieldDef[];
  data: Record<string, string>;
  results: HistoryResult[] | null;
  detail: DetailPayload | null;
}) {
  const [exportBusy, setExportBusy] = useState<null | "pdf" | "word">(null);
  const [copiedFlash, setCopiedFlash] = useState(false);

  const inputsForExport: ExportInputRow[] = useMemo(
    () =>
      fields
        .filter((f) => !!data[f.key] && data[f.key].trim() !== "")
        .map((f) => {
          const raw = data[f.key];
          const opt = f.options?.find((o) => o.value === raw);
          return {
            label: f.label,
            value: opt?.label ?? raw,
            unit: f.unit ?? null,
          };
        }),
    [fields, data],
  );

  const resultsForExport: ExportInputRow[] = useMemo(
    () =>
      (results ?? []).map((r) => ({
        label: r.label,
        value: r.value,
        unit: r.unit ?? null,
      })),
    [results],
  );

  const hasDetail = !!detail && detail.blocks.length > 0;

  const handlePdf = async () => {
    if (!hasDetail || !detail) return;
    Haptics.selectionAsync();
    setExportBusy("pdf");
    try {
      await exportDetailPdf({
        moduleName,
        categoryLabel,
        inputs: inputsForExport,
        results: resultsForExport,
        detail,
      });
    } catch (err) {
      console.error("PDF export failed", err);
    } finally {
      setExportBusy(null);
    }
  };

  const handleCopyWord = async () => {
    if (!hasDetail || !detail) return;
    Haptics.selectionAsync();
    setExportBusy("word");
    try {
      const ok = await copyDetailForWord({
        moduleName,
        categoryLabel,
        inputs: inputsForExport,
        results: resultsForExport,
        detail,
      });
      if (ok) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        setCopiedFlash(true);
        setTimeout(() => setCopiedFlash(false), 2500);
      }
    } catch (err) {
      console.error("Word copy failed", err);
    } finally {
      setExportBusy(null);
    }
  };

  return (
    <View style={styles.exportBar} testID="export-bar">
      <Pressable
        onPress={handlePdf}
        disabled={exportBusy !== null || !hasDetail}
        style={({ pressed }) => [
          styles.exportBtn,
          styles.exportBtnPrimary,
          (pressed || exportBusy === "pdf" || !hasDetail) && { opacity: 0.7 },
        ]}
        testID="export-pdf-button"
      >
        <MaterialCommunityIcons
          name={exportBusy === "pdf" ? "progress-clock" : "file-pdf-box"}
          size={18}
          color={colors.onBrandPrimary}
        />
        <Text style={styles.exportBtnTextPrimary}>
          {exportBusy === "pdf" ? "EXPORT…" : "EXPORTER PDF"}
        </Text>
      </Pressable>
      <Pressable
        onPress={handleCopyWord}
        disabled={exportBusy !== null || !hasDetail}
        style={({ pressed }) => [
          styles.exportBtn,
          styles.exportBtnSecondary,
          (pressed || exportBusy === "word" || !hasDetail) && { opacity: 0.7 },
        ]}
        testID="copy-word-button"
      >
        <MaterialCommunityIcons
          name={
            copiedFlash
              ? "check-bold"
              : exportBusy === "word"
                ? "progress-clock"
                : "content-copy"
          }
          size={18}
          color={copiedFlash ? colors.success : colors.brand}
        />
        <Text
          style={[
            styles.exportBtnTextSecondary,
            copiedFlash && { color: colors.success },
          ]}
        >
          {copiedFlash
            ? "COPIÉ ✓"
            : exportBusy === "word"
              ? "COPIE…"
              : "COPIER POUR WORD"}
        </Text>
      </Pressable>
    </View>
  );
}

function DetailTab({
  detail,
  onGo,
  moduleName,
  categoryLabel,
  fields,
  data,
  results,
}: {
  detail: DetailPayload | null;
  onGo: () => void;
  moduleName: string;
  categoryLabel: string;
  fields: FieldDef[];
  data: Record<string, string>;
  results: HistoryResult[] | null;
}) {
  const hasDetail = !!detail && detail.blocks.length > 0;

  if (!hasDetail || !detail) {
    return (
      <View style={styles.emptyResult} testID="detail-empty">
        <MaterialCommunityIcons
          name="file-document-outline"
          size={56}
          color={colors.onSurfaceTertiary}
        />
        <Text style={styles.emptyResultTitle}>Aucun détail</Text>
        <Text style={styles.emptyResultDesc}>
          Lancez un calcul pour afficher le détail complet — prêt pour capture
          d&apos;écran vers votre note de calcul.
        </Text>
        <Pressable
          onPress={onGo}
          style={styles.emptyResultBtn}
          testID="detail-goto-donnees"
        >
          <Text style={styles.emptyResultBtnText}>ALLER AUX DONNÉES</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.detailScroll}
      showsVerticalScrollIndicator={false}
      testID="detail-scroll"
    >
      <ExportBar
        moduleName={moduleName}
        categoryLabel={categoryLabel}
        fields={fields}
        data={data}
        results={results}
        detail={detail}
      />

      {detail.blocks.map((block, i) => (
        <DetailBlockView key={`b-${i}`} block={block} depth={0} />
      ))}
      <View style={styles.detailFooter}>
        <MaterialCommunityIcons
          name="information-outline"
          size={14}
          color={colors.onSurfaceTertiary}
        />
        <Text style={styles.detailFooterText}>
          PDF prêt pour vos rapports • Coller dans Word conserve les tableaux.
        </Text>
      </View>
    </ScrollView>
  );
}

function DetailBlockView({
  block,
  depth,
}: {
  block: DetailBlock;
  depth: number;
}) {
  return (
    <View
      style={[
        styles.detailBlock,
        depth > 0 && styles.detailSubBlock,
      ]}
      testID={`detail-block-${block.title}`}
    >
      <View
        style={[
          styles.detailBlockHeader,
          depth > 0 && styles.detailSubBlockHeader,
        ]}
      >
        <Text
          style={[
            styles.detailBlockTitle,
            depth > 0 && styles.detailSubBlockTitle,
          ]}
        >
          {block.title}
        </Text>
      </View>
      <View style={styles.detailTable}>
        {block.rows.map((r, i) => (
          <View
            key={`r-${i}`}
            style={[
              styles.detailRow,
              i !== block.rows.length - 1 && styles.detailRowDivider,
            ]}
          >
            <View style={styles.detailCellLabel}>
              <Text style={styles.detailLabel} numberOfLines={2}>
                {r.label}
              </Text>
              {r.unit ? (
                <Text style={styles.detailUnit}>[{r.unit}]</Text>
              ) : null}
            </View>
            <Text style={styles.detailValue} numberOfLines={1}>
              {r.value}
            </Text>
            <Text style={styles.detailFormula} numberOfLines={2}>
              {r.formula ?? "—"}
            </Text>
          </View>
        ))}
      </View>
      {block.subBlocks && block.subBlocks.length > 0 && (
        <View style={styles.detailSubWrap}>
          {block.subBlocks.map((sb, i) => (
            <DetailBlockView key={`sb-${i}`} block={sb} depth={depth + 1} />
          ))}
        </View>
      )}
    </View>
  );
}



function SelectSheet({
  field,
  currentValue,
  filterGroup,
  onClose,
  onPick,
}: {
  field: FieldDef | null;
  currentValue: string;
  filterGroup?: string;
  onClose: () => void;
  onPick: (v: string) => void;
}) {
  const { width } = useWindowDimensions();
  const isDesktop = width >= 768;

  const visible = field !== null;
  const options = (field?.options ?? []).filter((o) => {
    if (!field?.dependsOn) return true;
    return !filterGroup || o.group === filterGroup;
  });
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <Pressable
        style={[styles.modalBackdrop, isDesktop && styles.modalBackdropDesktop]}
        onPress={onClose}
      >
        <Pressable
          style={[styles.modalSheet, isDesktop && styles.modalSheetDesktop]}
          onPress={(e) => e.stopPropagation()}
        >
          {!isDesktop && <View style={styles.modalHandle} />}
          <Text style={styles.modalTitle}>{field?.label ?? ""}</Text>
          <ScrollView
            style={{ maxHeight: 360 }}
            showsVerticalScrollIndicator={false}
          >
            {options.map((opt) => {
              const active = opt.value === currentValue;
              return (
                <Pressable
                  key={opt.value}
                  onPress={() => onPick(opt.value)}
                  style={({ pressed }) => [
                    styles.optionRow,
                    active && styles.optionRowActive,
                    pressed && { opacity: 0.7 },
                  ]}
                  testID={`option-${opt.value}`}
                >
                  <Text
                    style={[
                      styles.optionText,
                      active && styles.optionTextActive,
                    ]}
                  >
                    {opt.label}
                  </Text>
                  {active && (
                    <MaterialCommunityIcons
                      name="check"
                      size={18}
                      color={colors.brand}
                    />
                  )}
                </Pressable>
              );
            })}
            {options.length === 0 && (
              <Text style={styles.optionText}>
                Aucune option pour ce type.
              </Text>
            )}
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.surface },
  errorTxt: { color: colors.error, padding: spacing.lg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.sm,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
    gap: spacing.sm,
  },
  backBtn: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.sm,
  },
  headerEyebrow: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 2,
    fontWeight: "700",
    fontFamily: fonts.text,
  },
  headerTitle: {
    color: colors.onSurface,
    fontSize: fontSize.xl,
    fontWeight: "700",
    fontFamily: fonts.display,
    letterSpacing: 0.5,
    marginTop: 2,
  },
  segmented: {
    flexDirection: "row",
    marginHorizontal: spacing.lg,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 3,
  },
  segment: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 10,
    borderRadius: radius.sm,
    gap: 6,
  },
  segmentActive: { backgroundColor: colors.brand },
  segmentText: {
    color: colors.onSurfaceSecondary,
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.5,
    fontFamily: fonts.text,
  },
  segmentTextActive: { color: colors.onBrandPrimary },
  errorBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    marginHorizontal: spacing.lg,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surfaceSecondary,
    borderLeftWidth: 3,
    borderLeftColor: colors.error,
    borderRadius: radius.sm,
  },
  errorBannerText: {
    flex: 1,
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
  },
  // Données
  formScroll: {
    padding: spacing.lg,
    paddingBottom: 120,
  },
  formCaption: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    marginBottom: spacing.lg,
    fontFamily: fonts.text,
  },
  field: { marginBottom: spacing.lg },
  fieldLabelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 6,
  },
  fieldLabel: {
    color: colors.onSurface,
    fontSize: fontSize.sm,
    fontWeight: "600",
    letterSpacing: 0.3,
    fontFamily: fonts.text,
  },
  fieldUnit: {
    color: colors.brandSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.5,
    fontFamily: fonts.mono,
  },
  input: {
    backgroundColor: colors.surfaceTertiary,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    color: colors.onSurface,
    fontSize: fontSize.lg,
    fontFamily: fonts.mono,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: 48,
  },
  inputText: {
    color: colors.onSurface,
    fontSize: fontSize.lg,
    fontFamily: fonts.mono,
  },
  // Advanced parameters (collapsible)
  advancedWrap: {
    marginTop: spacing.sm,
    marginBottom: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
    overflow: "hidden",
  },
  advancedHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    gap: spacing.sm,
  },
  advancedHeaderText: {
    flex: 1,
    color: colors.brandSecondary,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 2,
    fontFamily: fonts.text,
  },
  advancedBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: radius.sm,
    backgroundColor: colors.brandTertiary,
    minWidth: 20,
    alignItems: "center",
  },
  advancedBadgeText: {
    color: colors.brandSecondary,
    fontSize: 10,
    fontWeight: "800",
    fontFamily: fonts.mono,
  },
  advancedBody: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.xs,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  ctaBar: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    padding: spacing.lg,
    paddingBottom: Platform.OS === "ios" ? spacing.lg : spacing.lg,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  quotaLabel: {
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    fontWeight: "600",
    letterSpacing: 1,
    textAlign: "center",
    fontFamily: fonts.text,
    marginBottom: spacing.sm,
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
  ctaButtonPremium: {
    backgroundColor: "#B84600",
  },
  ctaText: {
    color: colors.onBrandPrimary,
    fontWeight: "800",
    letterSpacing: 2,
    fontSize: fontSize.base,
    fontFamily: fonts.text,
  },
  // Schéma
  schemaWrap: {
    flex: 1,
    margin: spacing.lg,
    marginTop: spacing.sm,
    borderRadius: radius.md,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  schemaCorner: {
    position: "absolute",
    bottom: spacing.sm,
    right: spacing.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
  },
  schemaCornerText: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 1,
    fontWeight: "700",
    fontFamily: fonts.mono,
  },
  // Résultat — mise en page split (résultats | diagramme)
  resultSplit: {
    gap: spacing.lg,
  },
  resultSplitLeft: {
    flex: 1,
    minWidth: 0,
  },
  resultSplitRight: {
    flex: 1,
    minWidth: 0,
  },
  // Diagramme de capacité
  diagramWrap: {
    marginTop: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    overflow: "hidden",
  },
  diagramHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.xs,
    gap: spacing.sm,
  },
  diagramTitle: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 1,
    fontWeight: "700",
    fontFamily: fonts.mono,
  },
  diagramCopyBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: spacing.sm,
    paddingVertical: 5,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
  },
  diagramCopyText: {
    color: colors.brandSecondary,
    fontSize: 9,
    letterSpacing: 0.5,
    fontWeight: "700",
    fontFamily: fonts.mono,
  },
  diagramHint: {
    color: colors.onSurfaceTertiary,
    fontSize: 10,
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
  },
  diagramCanvas: {
    height: DIAGRAM_HEIGHT,
    width: "100%",
  },
  // Case à cocher
  checkboxRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    marginBottom: spacing.md,
  },
  checkboxBox: {
    width: 22,
    height: 22,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxBoxChecked: {
    backgroundColor: colors.brand,
    borderColor: colors.brand,
  },
  checkboxLabel: {
    flex: 1,
    color: colors.onSurface,
    fontSize: fontSize.sm,
  },
  // Mise en page "split" (Données + courbe côte à côte)
  splitWrap: {
    flex: 1,
  },
  splitChartPaneDesktop: {
    flex: 1,
    margin: spacing.lg,
    marginBottom: spacing.sm,
  },
  splitChartPaneMobile: {
    height: 220,
    margin: spacing.lg,
    marginBottom: 0,
  },
  splitFormPane: {
    flex: 1,
  },
  spectrumWrap: {
    flex: 1,
    borderRadius: radius.md,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  // Résultat
  resultScroll: { padding: spacing.lg, paddingBottom: spacing.xl },
  resultHeader: { marginBottom: spacing.lg },
  resultEyebrow: {
    color: colors.brandSecondary,
    fontSize: 10,
    letterSpacing: 2,
    fontWeight: "700",
    fontFamily: fonts.text,
  },
  resultSubtitle: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    marginTop: 2,
    fontFamily: fonts.text,
  },
  metricRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: colors.surfaceSecondary,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    borderRadius: radius.sm,
    marginBottom: spacing.sm,
    borderLeftWidth: 3,
    borderLeftColor: colors.brand,
  },
  metricLabel: {
    flex: 1,
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
  },
  metricValueWrap: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: 6,
  },
  metricValue: {
    fontSize: fontSize.xl,
    fontWeight: "800",
    fontFamily: fonts.display,
    letterSpacing: 0.5,
  },
  metricUnit: {
    color: colors.onSurfaceTertiary,
    fontSize: fontSize.sm,
    fontFamily: fonts.mono,
  },
  savedNote: {
    flexDirection: "row",
    gap: 6,
    alignItems: "center",
    marginTop: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.surfaceSecondary,
    borderRadius: radius.sm,
    borderLeftWidth: 3,
    borderLeftColor: colors.success,
  },
  savedNoteText: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
  },
  emptyResult: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
    gap: spacing.sm,
  },
  emptyResultTitle: {
    color: colors.onSurface,
    fontSize: fontSize.xl,
    fontWeight: "700",
    fontFamily: fonts.display,
    letterSpacing: 1,
    marginTop: spacing.sm,
  },
  emptyResultDesc: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.sm,
    textAlign: "center",
    fontFamily: fonts.text,
  },
  emptyResultBtn: {
    marginTop: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: 12,
    backgroundColor: colors.brand,
    borderRadius: radius.sm,
  },
  emptyResultBtnText: {
    color: colors.onBrandPrimary,
    fontWeight: "800",
    letterSpacing: 1.5,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
  },
  // Modal
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.65)",
    justifyContent: "flex-end",
  },
  // Ordinateur (largeur ≥ 768) : popup centrée plutôt que feuille du bas.
  modalBackdropDesktop: {
    justifyContent: "center",
    alignItems: "center",
  },
  modalSheet: {
    backgroundColor: colors.surfaceSecondary,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: spacing.lg,
    paddingBottom: spacing.xl,
    borderTopWidth: 1,
    borderColor: colors.border,
  },
  modalSheetDesktop: {
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    borderBottomLeftRadius: radius.lg,
    borderBottomRightRadius: radius.lg,
    borderWidth: 1,
    width: "90%",
    maxWidth: 420,
    maxHeight: "75%",
    paddingBottom: spacing.lg,
  },
  modalHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.borderStrong,
    alignSelf: "center",
    marginBottom: spacing.md,
  },
  modalTitle: {
    color: colors.onSurface,
    fontSize: fontSize.lg,
    fontWeight: "700",
    fontFamily: fonts.display,
    letterSpacing: 1,
    marginBottom: spacing.sm,
  },
  optionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: spacing.md,
    borderRadius: radius.sm,
  },
  optionRowActive: { backgroundColor: colors.brandTertiary },
  optionText: {
    color: colors.onSurfaceSecondary,
    fontSize: fontSize.base,
    fontFamily: fonts.mono,
  },
  optionTextActive: { color: colors.brandSecondary, fontWeight: "700" },
  // ---- Detail tab (note de calcul style) ----
  detailScroll: {
    padding: spacing.lg,
    paddingBottom: spacing.xl,
  },
  detailBlock: {
    marginBottom: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
    overflow: "hidden",
  },
  detailSubBlock: {
    marginBottom: spacing.md,
    marginHorizontal: spacing.sm,
    marginTop: spacing.sm,
    borderColor: colors.borderStrong,
  },
  detailBlockHeader: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.brandTertiary,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    alignItems: "center",
  },
  detailSubBlockHeader: {
    backgroundColor: colors.surfaceTertiary,
  },
  detailBlockTitle: {
    color: colors.brandSecondary,
    fontFamily: fonts.display,
    fontSize: fontSize.base,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  detailSubBlockTitle: {
    color: colors.onSurface,
    fontSize: fontSize.sm,
    letterSpacing: 1,
  },
  detailTable: {
    paddingHorizontal: spacing.sm,
  },
  detailRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 8,
    paddingHorizontal: spacing.sm,
    gap: spacing.sm,
  },
  detailRowDivider: {
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  detailCellLabel: {
    flex: 1.2,
    minWidth: 0,
  },
  detailLabel: {
    color: colors.onSurface,
    fontSize: fontSize.sm,
    fontFamily: fonts.text,
    fontWeight: "600",
  },
  detailUnit: {
    color: colors.onSurfaceTertiary,
    fontSize: 10,
    fontFamily: fonts.mono,
    marginTop: 1,
  },
  detailValue: {
    flex: 0.7,
    color: colors.brandSecondary,
    fontSize: fontSize.sm,
    fontFamily: fonts.mono,
    fontWeight: "700",
    textAlign: "right",
  },
  detailFormula: {
    flex: 1.4,
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    fontFamily: fonts.mono,
    textAlign: "right",
    letterSpacing: 0.2,
  },
  detailSubWrap: {
    paddingBottom: spacing.sm,
  },
  detailFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: spacing.md,
  },
  detailFooterText: {
    color: colors.onSurfaceTertiary,
    fontSize: 11,
    fontStyle: "italic",
    fontFamily: fonts.text,
  },
  // ---- Export toolbar (Detail tab) ----
  exportBar: {
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  exportBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 12,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.sm,
    minHeight: 44,
  },
  exportBtnPrimary: {
    backgroundColor: colors.brand,
  },
  exportBtnSecondary: {
    borderWidth: 1,
    borderColor: colors.brand,
    backgroundColor: colors.brandTertiary,
  },
  exportBtnTextPrimary: {
    color: colors.onBrandPrimary,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1,
    fontFamily: fonts.text,
  },
  exportBtnTextSecondary: {
    color: colors.brand,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1,
    fontFamily: fonts.text,
  },
});
