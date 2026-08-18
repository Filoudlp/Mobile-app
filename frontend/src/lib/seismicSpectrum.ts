// Mirror (TypeScript) of Str-lib's norme.EC8.seisme.response_spectrum —
// France (NF EN 1998-1 + NA) et Suisse (SIA 261:2020, chapitre 16).
//
// Ce module sert UNIQUEMENT à l'aperçu visuel instantané de la courbe côté
// client (mise à jour à chaque saisie, sans aller-retour serveur). Le
// calcul officiel affiché dans Résultat/Détail vient toujours du backend
// (Str-lib est la source de vérité) — voir Web-app/backend/seisme_service.py.
//
// ⚠ Suisse : formules reconstruites depuis un PDF où les équations sont des
// images. France : classes de sol + Tableau 3.3 (type 2) lues dans le corps
// de l'Eurocode (fiable) ; zones sismiques (agR) et catégories d'importance
// (γI) reconstruites depuis la connaissance générale de l'arrêté du
// 22/10/2010 (non lu comme document source). Voir le docstring de
// response_spectrum.py pour le détail complet.

export type SoilParams = { S: number; TB: number; TC: number; TD: number };
export type Country = "FR" | "CH";

export const CH_ZONES: Record<string, number> = {
  Z1a: 0.6,
  Z1b: 0.8,
  Z2: 1.0,
  Z3a: 1.3,
  Z3b: 1.6,
};

export const CH_SOIL_CLASSES: Record<string, SoilParams> = {
  A: { S: 1.0, TB: 0.07, TC: 0.25, TD: 2.0 },
  B: { S: 1.2, TB: 0.08, TC: 0.35, TD: 2.0 },
  C: { S: 1.45, TB: 0.1, TC: 0.4, TD: 2.0 },
  D: { S: 1.7, TB: 0.1, TC: 0.5, TD: 2.0 },
  E: { S: 1.7, TB: 0.09, TC: 0.25, TD: 2.0 },
};

export const CH_IMPORTANCE_FACTORS: Record<string, number> = {
  I: 1.5,
  II: 1.2,
  III: 1.0,
};

// France — agR [m/s²] par zone (1 à 5) ; à confirmer contre l'arrêté du
// 22/10/2010 (non lu comme document source — voir docstring Python).
export const FR_ZONES: Record<string, number> = {
  "1": 0.4,
  "2": 0.7,
  "3": 1.1,
  "4": 1.6,
  "5": 3.0,
};

// France — NF EN 1998-1, Tableau 3.3 (spectre de type 2).
export const FR_SOIL_CLASSES: Record<string, SoilParams> = {
  A: { S: 1.0, TB: 0.05, TC: 0.25, TD: 1.2 },
  B: { S: 1.35, TB: 0.05, TC: 0.25, TD: 1.2 },
  C: { S: 1.5, TB: 0.1, TC: 0.25, TD: 1.2 },
  D: { S: 1.8, TB: 0.1, TC: 0.3, TD: 1.2 },
  E: { S: 1.6, TB: 0.05, TC: 0.25, TD: 1.2 },
};

// France — γI par catégorie d'importance (I à IV) ; à confirmer (idem FR_ZONES).
export const FR_IMPORTANCE_FACTORS: Record<string, number> = {
  I: 0.8,
  II: 1.0,
  III: 1.2,
  IV: 1.4,
};

const BETA_FLOOR = 0.2;

export function etaDamping(xiPercent = 5): number {
  return Math.max(Math.sqrt(10 / (5 + xiPercent)), 0.55);
}

/** Se(T) — forme normalisée EC8 (4 branches), ag déjà mis à l'échelle
 * (= γI·agR en France, = agd en Suisse). */
export function elasticSe(
  T: number,
  ag: number,
  soil: SoilParams,
  eta: number,
): number {
  const { S, TB, TC, TD } = soil;
  if (T < TB) return ag * S * (1 + (T / TB) * (2.5 * eta - 1));
  if (T <= TC) return ag * S * 2.5 * eta;
  if (T <= TD) return ag * S * 2.5 * eta * (TC / T);
  return ag * S * 2.5 * eta * ((TC * TD) / (T * T));
}

/** Sd(T) — forme normalisée EC8 (4 branches, plancher β·ag). */
export function designSd(
  T: number,
  ag: number,
  soil: SoilParams,
  q: number,
): number {
  const { S, TB, TC, TD } = soil;
  const floor = BETA_FLOOR * ag;
  let raw: number;
  if (T < TB) raw = ag * S * (2 / 3 + (T / TB) * (2.5 / q - 2 / 3));
  else if (T <= TC) raw = ag * S * (2.5 / q);
  else if (T <= TD) raw = ag * S * (2.5 / q) * (TC / T);
  else raw = ag * S * (2.5 / q) * ((TC * TD) / (T * T));
  return Math.max(raw, floor);
}

export type SpectrumInputs = {
  country: Country;
  zone: string;
  soilClass: string;
  q: number;
  importanceClass: string;
  xiPercent: number;
};

export type SpectrumCurves = {
  T: number[];
  Se: number[];
  Sd: number[];
  ag: number;
  soil: SoilParams;
};

function resolveAg(inputs: SpectrumInputs): number | null {
  if (inputs.country === "FR") {
    const agR = FR_ZONES[inputs.zone];
    const gammaI = FR_IMPORTANCE_FACTORS[inputs.importanceClass] ?? 1.0;
    return agR === undefined ? null : agR * gammaI;
  }
  const agd = CH_ZONES[inputs.zone];
  return agd === undefined ? null : agd;
}

function resolveSoil(inputs: SpectrumInputs): SoilParams | null {
  const table = inputs.country === "FR" ? FR_SOIL_CLASSES : CH_SOIL_CLASSES;
  return table[inputs.soilClass] ?? null;
}

/** null si zone/classe de sol invalides (saisie incomplète). */
export function buildSpectrumCurves(
  inputs: SpectrumInputs,
  n = 60,
  Tmax = 4,
): SpectrumCurves | null {
  const ag = resolveAg(inputs);
  const soil = resolveSoil(inputs);
  if (ag === null || !soil) return null;
  const eta = etaDamping(inputs.xiPercent);
  const q = inputs.q > 0 ? inputs.q : 1.5;
  const step = Tmax / (n - 1);
  const T: number[] = [];
  const Se: number[] = [];
  const Sd: number[] = [];
  for (let i = 0; i < n; i++) {
    const t = i * step;
    T.push(t);
    Se.push(elasticSe(t, ag, soil, eta));
    Sd.push(designSd(t, ag, soil, q));
  }
  return { T, Se, Sd, ag, soil };
}

/** Point exact (Se(T), Sd(T)) pour une période T donnée — pour le marqueur
 * interactif sur le graphique. null si les entrées sont incomplètes. */
export function pointAt(
  inputs: SpectrumInputs,
  T: number,
): { Se: number; Sd: number } | null {
  const ag = resolveAg(inputs);
  const soil = resolveSoil(inputs);
  if (ag === null || !soil || !Number.isFinite(T) || T < 0) return null;
  const eta = etaDamping(inputs.xiPercent);
  const q = inputs.q > 0 ? inputs.q : 1.5;
  return { Se: elasticSe(T, ag, soil, eta), Sd: designSd(T, ag, soil, q) };
}
