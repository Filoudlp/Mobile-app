// Module catalog. The 'Acier' category is active (UI-only).
// Béton armé / Bois listed as upcoming.

export type FieldType = "number" | "select" | "checkbox";

export type FieldDef = {
  key: string;
  label: string;
  unit?: string;
  type: FieldType;
  options?: { label: string; value: string; group?: string }[];
  /** Key of another field whose value filters `options` by matching `group`. */
  dependsOn?: string;
  /** Pour `checkbox` : "1" = coché, "" ou "0" = décoché. */
  defaultValue: string;
  placeholder?: string;
  advanced?: boolean;
  /** Only render this field when `data[showIf.key] === showIf.value`. */
  showIf?: { key: string; value: string };
};

export type ModuleDef = {
  id: string;
  categoryId: CategoryId;
  name: string;
  description: string;
  icon: string; // MaterialCommunityIcons name
  schemaType?: "beam" | "column" | "bolt" | "roof" | "wind" | "rc-column";
  /** "split" : affiche Données et Schéma côte à côte (pas d'onglet Schéma
   * séparé) — pour les modules avec un aperçu qui doit rester visible
   * pendant la saisie (ex. courbe de spectre). "tabs" (défaut) : 4 onglets
   * classiques Données / Schéma / Résultat / Détail. */
  layout?: "tabs" | "split";
  fields: FieldDef[];
};

export type CategoryId = "acier" | "beton" | "bois" | "climat" | "seisme";

export type Category = {
  id: CategoryId;
  name: string;
  shortName: string;
  imageKey: "category_acier" | "category_beton" | "category_bois" | "category_climat" | "category_seisme";
  available: boolean;
};

export const CATEGORIES: Category[] = [
  {
    id: "acier",
    name: "Acier",
    shortName: "ACIER",
    imageKey: "category_acier",
    available: true,
  },
  {
    id: "climat",
    name: "Actions climatiques",
    shortName: "CLIMAT",
    imageKey: "category_climat",
    available: true,
  },
  {
    id: "seisme",
    name: "Actions sismiques",
    shortName: "SÉISME",
    imageKey: "category_seisme",
    available: true,
  },
  {
    id: "beton",
    name: "Béton armé",
    shortName: "BÉTON ARMÉ",
    imageKey: "category_beton",
    available: true,
  },
  {
    id: "bois",
    name: "Bois",
    shortName: "BOIS",
    imageKey: "category_bois",
    available: false,
  },
];

export const CATEGORY_IMAGES: Record<Category["imageKey"], string> = {
  category_acier:
    "https://images.unsplash.com/photo-1493476523860-a6de6ce1b0c3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzJ8MHwxfHNlYXJjaHwxfHxzdGVlbCUyMHN0cnVjdHVyZSUyMGVuZ2luZWVyaW5nJTIwY29uc3RydWN0aW9ufGVufDB8fHx8MTc4MTc3NTM4NXww&ixlib=rb-4.1.0&q=85",
  category_beton:
    "https://images.pexels.com/photos/37475275/pexels-photo-37475275.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
  category_bois:
    "https://images.unsplash.com/photo-1563874093519-ca5eda5cd776?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2OTF8MHwxfHNlYXJjaHwxfHx3b29kJTIwdGltYmVyJTIwZnJhbWluZyUyMGFyY2hpdGVjdHVyZXxlbnwwfHx8fDE3ODE3NzUzODV8MA&ixlib=rb-4.1.0&q=85",
  // Réutilise l'image acier (pas de nouvelle URL externe non vérifiée).
  category_climat:
    "https://images.unsplash.com/photo-1493476523860-a6de6ce1b0c3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzJ8MHwxfHNlYXJjaHwxfHxzdGVlbCUyMHN0cnVjdHVyZSUyMGVuZ2luZWVyaW5nJTIwY29uc3RydWN0aW9ufGVufDB8fHx8MTc4MTc3NTM4NXww&ixlib=rb-4.1.0&q=85",
  // Idem — réutilise l'image acier.
  category_seisme:
    "https://images.unsplash.com/photo-1493476523860-a6de6ce1b0c3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzJ8MHwxfHNlYXJjaHwxfHxzdGVlbCUyMHN0cnVjdHVyZSUyMGVuZ2luZWVyaW5nJTIwY29uc3RydWN0aW9ufGVufDB8fHx8MTc4MTc3NTM4NXww&ixlib=rb-4.1.0&q=85",
};

const PROFILE_FAMILIES = [
  { label: "HEA", value: "HEA" },
  { label: "HEB", value: "HEB" },
  { label: "HEM", value: "HEM" },
  { label: "IPE", value: "IPE" },
  { label: "IPN", value: "IPN" },
  { label: "HD", value: "HD" },
  { label: "HL", value: "HL" },
  { label: "HP", value: "HP" },
];

// Profile sizes tagged with a `group` = family. The Sheet filters by
// data[dependsOn] === option.group so we only show the sizes of the current
// family.
const SIZES_HEA = [100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300];
const SIZES_HEB = SIZES_HEA;
const SIZES_HEM = SIZES_HEA;
const SIZES_IPE = [80, 100, 120, 140, 160, 180, 200, 220, 240, 270, 300, 330, 360, 400, 450, 500];
const SIZES_IPN = [80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320, 340, 360, 380, 400];
const SIZES_HD = [260, 320, 360, 400];
const SIZES_HL = [920, 1000, 1100];
const SIZES_HP = [200, 220, 260, 305, 320, 360];

const PROFILE_SIZES = [
  ...SIZES_HEA.map((s) => ({ label: `HEA ${s}`, value: `HEA ${s}`, group: "HEA" })),
  ...SIZES_HEB.map((s) => ({ label: `HEB ${s}`, value: `HEB ${s}`, group: "HEB" })),
  ...SIZES_HEM.map((s) => ({ label: `HEM ${s}`, value: `HEM ${s}`, group: "HEM" })),
  ...SIZES_IPE.map((s) => ({ label: `IPE ${s}`, value: `IPE ${s}`, group: "IPE" })),
  ...SIZES_IPN.map((s) => ({ label: `IPN ${s}`, value: `IPN ${s}`, group: "IPN" })),
  ...SIZES_HD.map((s) => ({ label: `HD ${s}`, value: `HD ${s}`, group: "HD" })),
  ...SIZES_HL.map((s) => ({ label: `HL ${s}`, value: `HL ${s}`, group: "HL" })),
  ...SIZES_HP.map((s) => ({ label: `HP ${s}`, value: `HP ${s}`, group: "HP" })),
];

const STEEL_GRADES = [
  { label: "S235", value: "S235" },
  { label: "S275", value: "S275" },
  { label: "S355", value: "S355" },
  { label: "S460", value: "S460" },
];

const CURVES = [
  { label: "Auto (selon Tab. 6.2)", value: "auto" },
  { label: "a0", value: "a0" },
  { label: "a", value: "a" },
  { label: "b", value: "b" },
  { label: "c", value: "c" },
  { label: "d", value: "d" },
];

const NORMES_ACIER = [
  { label: "Eurocode 3 — EN 1993-1-1 / 1-5", value: "EC3" },
  { label: "SIA 263:2013", value: "SIA263" },
];

const SECTION_CLASSES = [
  { label: "Classe 1 (plastique)", value: "1" },
  { label: "Classe 2 (compacte)", value: "2" },
  { label: "Classe 3 (élastique)", value: "3" },
];

const PROFILE_FABRICATION = [
  { label: "Laminé", value: "rolled" },
  { label: "Soudé (PRS)", value: "welded" },
];

const BEAM_SUPPORTS = [
  { label: "Bi-articulée", value: "simply_supported" },
  { label: "Console", value: "cantilever" },
  { label: "Bi-encastrée", value: "fixed_fixed" },
  { label: "Encastrée-articulée", value: "fixed_pinned" },
];

const DEFLECTION_LIMITS = [
  { label: "Plancher courant — L/250", value: "floor_general" },
  { label: "Cloisons fragiles — L/300", value: "floor_brittle_partitions" },
  { label: "Supportant poteaux — L/400", value: "floor_supporting_columns" },
  { label: "Toiture — L/200", value: "roof_general" },
  { label: "Console — L/150", value: "cantilever" },
];

const NORMES_BETON = [
  { label: "Eurocode 2 — EN 1992-1-1", value: "EC2" },
  { label: "SIA 262:2013", value: "SIA262" },
];

// Les trois méthodes de prise en compte du second ordre. La courbure
// nominale est la valeur par défaut. « Rigidité » et « forfaitaire »
// sont propres à l'EC2 / aux RP françaises : en SIA 262 le §4.3.7
// (excentricités cumulées) s'applique quelle que soit la sélection.
const METHODES_BETON = [
  { label: "Courbure nominale — EC2 §5.8.8", value: "courbure" },
  { label: "Rigidité nominale — EC2 §5.8.7", value: "rigidite" },
  { label: "Forfaitaire — RP FFB", value: "forfaitaire" },
];

const SECTION_SHAPES = [
  { label: "Rectangulaire", value: "rect" },
  { label: "Circulaire", value: "circ" },
];

const CONCRETE_CLASSES = [
  "C20/25", "C25/30", "C30/37", "C35/45", "C40/50", "C45/55", "C50/60",
].map((c) => ({ label: c, value: c }));

const REBAR_GRADES = ["B500A", "B500B", "B500C", "B700B"].map((g) => ({
  label: g,
  value: g,
}));

const NEIGE_COUNTRIES = [
  { label: "France — NF EN 1991-1-3/NA", value: "FR" },
  { label: "Suisse — SIA 261", value: "CH" },
];

const NEIGE_ZONES_FR = ["A1", "A2", "B1", "B2", "C1", "C2", "D", "E"].map((z) => ({
  label: `Zone ${z}`,
  value: z,
}));

// Options groupées par pays — la France n'a pas l'option "exposé" (0,8),
// seulement normal / abrité (Ce = 1,0 / 1,25). La Suisse a les 3 (SIA 261).
const NEIGE_EXPOSURE = [
  { label: "Site normal", value: "normal", group: "FR" },
  { label: "Site abrité", value: "abrite", group: "FR" },
  { label: "Site exposé au vent", value: "expose", group: "CH" },
  { label: "Site normal", value: "normal", group: "CH" },
  { label: "Site abrité", value: "abrite", group: "CH" },
];

const VENT_COUNTRIES = [
  { label: "France — NF EN 1991-1-4/NA", value: "FR" },
  { label: "Suisse — SIA 261", value: "CH" },
];

const VENT_REGIONS_FR = [
  { label: "Région 1 (vb,0 = 22 m/s)", value: "1" },
  { label: "Région 2 (vb,0 = 24 m/s)", value: "2" },
  { label: "Région 3 (vb,0 = 26 m/s)", value: "3" },
  { label: "Région 4 (vb,0 = 28 m/s)", value: "4" },
  { label: "Guadeloupe (vb,0 = 36 m/s)", value: "guadeloupe" },
  { label: "Guyane (vb,0 = 17 m/s)", value: "guyane" },
  { label: "Martinique (vb,0 = 32 m/s)", value: "martinique" },
  { label: "Réunion (vb,0 = 34 m/s)", value: "reunion" },
];

// Catégories de terrain groupées par pays — tables distinctes (Tableau
// 4.1(NA) en France, Tableau 4 en Suisse), pas les mêmes clés.
const VENT_TERRAIN_CATEGORIES = [
  { label: "0 — Mer, zone côtière exposée", value: "0", group: "FR" },
  { label: "II — Rase campagne", value: "II", group: "FR" },
  { label: "IIIa — Campagne avec haies, bocage", value: "IIIa", group: "FR" },
  { label: "IIIb — Zones urbanisées/industrielles", value: "IIIb", group: "FR" },
  { label: "IV — Zones urbaines denses, forêts", value: "IV", group: "FR" },
  { label: "II — Rive lacustre", value: "II", group: "CH" },
  { label: "IIa — Grande plaine", value: "IIa", group: "CH" },
  { label: "III — Localité, milieu rural", value: "III", group: "CH" },
  { label: "IV — Zone urbaine étendue", value: "IV", group: "CH" },
];

const SEISME_COUNTRIES = [
  { label: "France — NF EN 1998-1/NA", value: "FR" },
  { label: "Suisse — SIA 261", value: "CH" },
];

// Zone/classe de sol/catégorie d'importance groupées par pays — options
// séparées (valeurs et tables distinctes), cascade automatique au
// changement de pays (comme country->terrain_category pour le vent).
const SEISME_ZONES = [
  { label: "Zone 1 (très faible)", value: "1", group: "FR" },
  { label: "Zone 2 (faible)", value: "2", group: "FR" },
  { label: "Zone 3 (modérée)", value: "3", group: "FR" },
  { label: "Zone 4 (moyenne)", value: "4", group: "FR" },
  { label: "Zone 5 (forte — Antilles)", value: "5", group: "FR" },
  { label: "Zone Z1a", value: "Z1a", group: "CH" },
  { label: "Zone Z1b", value: "Z1b", group: "CH" },
  { label: "Zone Z2", value: "Z2", group: "CH" },
  { label: "Zone Z3a", value: "Z3a", group: "CH" },
  { label: "Zone Z3b", value: "Z3b", group: "CH" },
];

const SEISME_SOIL_CLASSES = ["A", "B", "C", "D", "E"].flatMap((c) => [
  { label: `Classe ${c}`, value: c, group: "FR" },
  { label: `Classe ${c}`, value: c, group: "CH" },
]);

const SEISME_IMPORTANCE_CLASSES = [
  { label: "I — Risque minime", value: "I", group: "FR" },
  { label: "II — Risque normal (courant)", value: "II", group: "FR" },
  { label: "III — Établissements scolaires, ERP", value: "III", group: "FR" },
  { label: "IV — Sécurité civile, hôpitaux", value: "IV", group: "FR" },
  { label: "I — Infrastructure vitale", value: "I", group: "CH" },
  { label: "II — Forte occupation / importante", value: "II", group: "CH" },
  { label: "III — Ouvrages courants", value: "III", group: "CH" },
];

export const MODULES: ModuleDef[] = [
  {
    id: "acier-poutre-flechie",
    categoryId: "acier",
    name: "Poutre acier — EC3 / SIA 263",
    description:
      "Flexion + cisaillement + voilement d'âme + déversement + interactions + flèche",
    icon: "format-horizontal-align-center",
    schemaType: "beam",
    fields: [
      // === Norme & section ===
      {
        key: "norme",
        label: "Norme de vérification",
        type: "select",
        options: NORMES_ACIER,
        defaultValue: "EC3",
      },
      {
        key: "profile_family",
        label: "Type de profilé",
        type: "select",
        options: PROFILE_FAMILIES,
        defaultValue: "IPE",
      },
      {
        key: "profile",
        label: "Profilé",
        type: "select",
        options: PROFILE_SIZES,
        dependsOn: "profile_family",
        defaultValue: "IPE 300",
      },
      {
        key: "grade",
        label: "Nuance d'acier",
        type: "select",
        options: STEEL_GRADES,
        defaultValue: "S235",
      },
      // === Géométrie ===
      {
        key: "L_m",
        label: "Portée de la poutre",
        unit: "m",
        type: "number",
        defaultValue: "6",
        placeholder: "6.00",
      },
      {
        key: "Lcr_LT_m",
        label: "Longueur de déversement",
        unit: "m",
        type: "number",
        defaultValue: "",
        placeholder: "= portée si vide",
      },
      // === Efforts ELU ===
      {
        key: "My_ed",
        label: "Moment My,Ed",
        unit: "kN·m",
        type: "number",
        defaultValue: "120",
        placeholder: "120",
      },
      {
        key: "Vz_ed",
        label: "Effort tranchant Vz,Ed",
        unit: "kN",
        type: "number",
        defaultValue: "80",
        placeholder: "80",
      },
      {
        key: "N_ed",
        label: "Effort normal N,Ed (+ traction)",
        unit: "kN",
        type: "number",
        defaultValue: "0",
        placeholder: "0",
      },
      // === ELS ===
      {
        key: "q_els",
        label: "Charge de service (flèche)",
        unit: "kN/m",
        type: "number",
        defaultValue: "12",
        placeholder: "12",
      },
      {
        key: "limit_type",
        label: "Limite de flèche",
        type: "select",
        options: DEFLECTION_LIMITS,
        defaultValue: "floor_general",
      },
      // === Avancé ===
      {
        key: "Mz_ed",
        label: "Moment Mz,Ed",
        unit: "kN·m",
        type: "number",
        defaultValue: "0",
        advanced: true,
      },
      {
        key: "Vy_ed",
        label: "Effort tranchant Vy,Ed",
        unit: "kN",
        type: "number",
        defaultValue: "0",
        advanced: true,
      },
      {
        key: "section_class",
        label: "Classe de section",
        type: "select",
        options: SECTION_CLASSES,
        defaultValue: "1",
        advanced: true,
      },
      {
        key: "profile_type",
        label: "Fabrication",
        type: "select",
        options: PROFILE_FABRICATION,
        defaultValue: "rolled",
        advanced: true,
      },
      {
        key: "support",
        label: "Conditions d'appui (flèche)",
        type: "select",
        options: BEAM_SUPPORTS,
        defaultValue: "simply_supported",
        advanced: true,
      },
      {
        key: "a_stiffener_m",
        label: "Espacement raidisseurs d'âme",
        unit: "m",
        type: "number",
        defaultValue: "",
        placeholder: "vide = âme non raidie",
        advanced: true,
      },
      {
        key: "psi",
        label: "Rapport des moments ψ",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
      {
        key: "C1",
        label: "Coefficient C1 (déversement)",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
    ],
  },
  {
    id: "acier-poteau-comprime",
    categoryId: "acier",
    name: "Poteau acier — EC3 / SIA 263",
    description: "Compression + flexion biaxiale + cisaillement + flambement + déversement",
    icon: "format-line-weight",
    schemaType: "column",
    fields: [
      // === Section (visible) ===
      {
        key: "profile_family",
        label: "Type de profilé",
        type: "select",
        options: PROFILE_FAMILIES,
        defaultValue: "HEA",
      },
      {
        key: "profile",
        label: "Profilé",
        type: "select",
        options: PROFILE_SIZES,
        dependsOn: "profile_family",
        defaultValue: "HEA 200",
      },
      {
        key: "grade",
        label: "Nuance d'acier",
        type: "select",
        options: STEEL_GRADES,
        defaultValue: "S275",
      },
      // === Géométrie (visible) ===
      {
        key: "length_m",
        label: "Longueur de la barre",
        unit: "m",
        type: "number",
        defaultValue: "3",
        placeholder: "3.00",
      },
      // === Efforts (visible) ===
      {
        key: "N_ed",
        label: "Effort normal N,Ed",
        unit: "kN",
        type: "number",
        defaultValue: "500",
        placeholder: "500",
      },
      {
        key: "My_ed",
        label: "Moment My,Ed",
        unit: "kN·m",
        type: "number",
        defaultValue: "0",
        placeholder: "0",
      },
      {
        key: "Mz_ed",
        label: "Moment Mz,Ed",
        unit: "kN·m",
        type: "number",
        defaultValue: "0",
        placeholder: "0",
      },
      {
        key: "Vz_ed",
        label: "Effort tranchant Vz,Ed",
        unit: "kN",
        type: "number",
        defaultValue: "0",
        placeholder: "0",
      },
      {
        key: "Vy_ed",
        label: "Effort tranchant Vy,Ed",
        unit: "kN",
        type: "number",
        defaultValue: "0",
        placeholder: "0",
      },
      // === Avancés ===
      {
        key: "norme",
        label: "Norme de calcul",
        type: "select",
        options: [
          { label: "EC3 (NF EN 1993-1-1)", value: "EC3" },
          { label: "SIA 263", value: "SIA263" },
        ],
        defaultValue: "EC3",
        advanced: true,
      },
      {
        key: "Ky",
        label: "Coefficient longueur Ky (Lcr,y = Ky·L)",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
      {
        key: "Kz",
        label: "Coefficient longueur Kz (Lcr,z = Kz·L)",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
      {
        key: "LcrLT_m",
        label: "Longueur de déversement Lcr,LT (défaut = L)",
        unit: "m",
        type: "number",
        defaultValue: "",
        placeholder: "auto (= L)",
        advanced: true,
      },
      {
        key: "curve_y",
        label: "Courbe de flambement axe y",
        type: "select",
        options: CURVES,
        defaultValue: "auto",
        advanced: true,
      },
      {
        key: "curve_z",
        label: "Courbe de flambement axe z",
        type: "select",
        options: CURVES,
        defaultValue: "auto",
        advanced: true,
      },
      {
        key: "curve_LT",
        label: "Courbe de déversement LT",
        type: "select",
        options: CURVES,
        defaultValue: "auto",
        advanced: true,
      },
      {
        key: "interaction_method",
        label: "Méthode interaction M-N",
        type: "select",
        options: [
          { label: "Méthode 2 (Annexe B) — recommandée FR", value: "2" },
          { label: "Méthode 1 (Annexe A)", value: "1" },
        ],
        defaultValue: "2",
        advanced: true,
      },
      {
        key: "psi_y",
        label: "Diagramme moment ψy (Mmin/Mmax)",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
      {
        key: "psi_z",
        label: "Diagramme moment ψz",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
      {
        key: "C1",
        label: "Coefficient C1 (déversement)",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
      {
        key: "Cmy",
        label: "Cmy (moment équivalent y)",
        type: "number",
        defaultValue: "0.9",
        advanced: true,
      },
      {
        key: "Cmz",
        label: "Cmz (moment équivalent z)",
        type: "number",
        defaultValue: "0.9",
        advanced: true,
      },
      {
        key: "section_class",
        label: "Classe de section",
        type: "select",
        options: [
          { label: "1", value: "1" },
          { label: "2", value: "2" },
          { label: "3", value: "3" },
        ],
        defaultValue: "1",
        advanced: true,
      },
      {
        key: "gamma_m0",
        label: "γM0 (auto selon norme)",
        type: "number",
        defaultValue: "",
        placeholder: "auto",
        advanced: true,
      },
      {
        key: "gamma_m1",
        label: "γM1 (auto selon norme)",
        type: "number",
        defaultValue: "",
        placeholder: "auto",
        advanced: true,
      },
    ],
  },
  {
    id: "neige-toiture",
    categoryId: "climat",
    name: "Charge de neige sur toiture",
    description: "Charge caractéristique au sol et sur toiture — France / Suisse",
    icon: "snowflake",
    schemaType: "roof",
    fields: [
      {
        key: "country",
        label: "Pays / norme",
        type: "select",
        options: NEIGE_COUNTRIES,
        defaultValue: "FR",
      },
      {
        key: "zone",
        label: "Zone de neige",
        type: "select",
        options: NEIGE_ZONES_FR,
        defaultValue: "A1",
        showIf: { key: "country", value: "FR" },
      },
      {
        key: "altitude_m",
        label: "Altitude du site",
        unit: "m",
        type: "number",
        defaultValue: "300",
        placeholder: "300",
      },
      {
        key: "h0_m",
        label: "Altitude de référence h0",
        unit: "m",
        type: "number",
        defaultValue: "500",
        placeholder: "500",
        showIf: { key: "country", value: "CH" },
      },
      {
        key: "angle_deg",
        label: "Angle de toiture α",
        unit: "°",
        type: "number",
        defaultValue: "20",
        placeholder: "20",
      },
      {
        key: "exposure",
        label: "Exposition au vent",
        type: "select",
        options: NEIGE_EXPOSURE,
        dependsOn: "country",
        defaultValue: "normal",
      },
      {
        key: "Ct",
        label: "Coefficient thermique Ct",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
    ],
  },
  {
    id: "vent-facade",
    categoryId: "climat",
    name: "Pression du vent sur façade",
    description: "Pression dynamique et coefficients de pression — murs verticaux, France / Suisse",
    icon: "weather-windy",
    schemaType: "wind",
    fields: [
      {
        key: "country",
        label: "Pays / norme",
        type: "select",
        options: VENT_COUNTRIES,
        defaultValue: "FR",
      },
      {
        key: "region",
        label: "Région climatique",
        type: "select",
        options: VENT_REGIONS_FR,
        defaultValue: "2",
        showIf: { key: "country", value: "FR" },
      },
      {
        key: "qp0_kn_m2",
        label: "Pression de référence qp0",
        unit: "kN/m²",
        type: "number",
        defaultValue: "0.9",
        placeholder: "0.9",
        showIf: { key: "country", value: "CH" },
      },
      {
        key: "terrain_category",
        label: "Catégorie de terrain",
        type: "select",
        options: VENT_TERRAIN_CATEGORIES,
        dependsOn: "country",
        defaultValue: "II",
      },
      {
        key: "h_m",
        label: "Hauteur du bâtiment h",
        unit: "m",
        type: "number",
        defaultValue: "9",
        placeholder: "9.00",
      },
      {
        key: "b_m",
        label: "Largeur au vent b",
        unit: "m",
        type: "number",
        defaultValue: "15",
        placeholder: "15.00",
      },
      {
        key: "d_m",
        label: "Profondeur d",
        unit: "m",
        type: "number",
        defaultValue: "25",
        placeholder: "25.00",
      },
      {
        key: "cscd",
        label: "Facteur structural cscd",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
      },
      {
        key: "cdir",
        label: "Coefficient de direction cdir",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
        showIf: { key: "country", value: "FR" },
      },
      {
        key: "cseason",
        label: "Coefficient de saison cseason",
        type: "number",
        defaultValue: "1.0",
        advanced: true,
        showIf: { key: "country", value: "FR" },
      },
    ],
  },
  {
    id: "beton-poteau",
    categoryId: "beton",
    name: "Poteau béton — EC2 / SIA 262",
    description:
      "Second ordre : forfaitaire / courbure nominale / rigidité nominale + diagramme de capacité",
    icon: "view-column",
    schemaType: "rc-column",
    fields: [
      // === Norme & méthode ===
      // === Section ===
      {
        key: "shape",
        label: "Forme de section",
        type: "select",
        options: SECTION_SHAPES,
        defaultValue: "rect",
      },
      {
        key: "b_mm",
        label: "Largeur b",
        unit: "mm",
        type: "number",
        defaultValue: "300",
        placeholder: "300",
        showIf: { key: "shape", value: "rect" },
      },
      {
        key: "h_mm",
        label: "Hauteur h (plan de flexion)",
        unit: "mm",
        type: "number",
        defaultValue: "400",
        placeholder: "400",
        showIf: { key: "shape", value: "rect" },
      },
      {
        key: "D_mm",
        label: "Diamètre D",
        unit: "mm",
        type: "number",
        defaultValue: "400",
        placeholder: "400",
        showIf: { key: "shape", value: "circ" },
      },
      // === Matériaux ===
      {
        key: "concrete_class",
        label: "Classe de béton",
        type: "select",
        options: CONCRETE_CLASSES,
        defaultValue: "C25/30",
      },
      {
        key: "As_cm2",
        label: "Section d'armatures As",
        unit: "cm²",
        type: "number",
        defaultValue: "12.56",
        placeholder: "12.56",
      },
      // === Géométrie ===
      {
        key: "l0_m",
        label: "Longueur efficace l0",
        unit: "m",
        type: "number",
        defaultValue: "3.5",
        placeholder: "3.50",
      },
      // === Efforts ===
      {
        key: "N_ed_kn",
        label: "Effort normal NEd (compression)",
        unit: "kN",
        type: "number",
        defaultValue: "900",
        placeholder: "900",
      },
      {
        key: "M0_top_knm",
        label: "Moment en tête M0,top",
        unit: "kN·m",
        type: "number",
        defaultValue: "20",
        placeholder: "20",
      },
      {
        key: "M0_bot_knm",
        label: "Moment en pied M0,bot",
        unit: "kN·m",
        type: "number",
        defaultValue: "10",
        placeholder: "10",
      },
      // === Graphique ===
      {
        key: "show_diagram",
        label: "Afficher le diagramme de capacité (N-M)",
        type: "checkbox",
        defaultValue: "1",
      },
      // === Avancé ===
      {
        key: "norme",
        label: "Norme de vérification",
        type: "select",
        options: NORMES_BETON,
        defaultValue: "EC2",
        advanced: true,
      },
      {
        key: "methode",
        label: "Méthode de vérification",
        type: "select",
        options: METHODES_BETON,
        defaultValue: "courbure",
        advanced: true,
      },
      {
        key: "rebar_grade",
        label: "Nuance d'armature",
        type: "select",
        options: REBAR_GRADES,
        defaultValue: "B500B",
        advanced: true,
      },
      {
        key: "d_prime_mm",
        label: "Enrobage mécanique d'",
        unit: "mm",
        type: "number",
        defaultValue: "50",
        advanced: true,
      },
      {
        key: "phi_ef",
        label: "Coefficient de fluage φef",
        type: "number",
        defaultValue: "2.0",
        advanced: true,
      },
      {
        key: "c_curvature",
        label: "Coefficient c (courbure)",
        type: "number",
        defaultValue: "10",
        advanced: true,
      },
      {
        key: "c0_stiffness",
        label: "Coefficient c0 (rigidité)",
        type: "number",
        defaultValue: "8",
        advanced: true,
      },
    ],
  },
  {
    id: "seisme-spectre",
    categoryId: "seisme",
    name: "Spectre de réponse sismique",
    description: "Spectre élastique et de dimensionnement — France (EC8) / Suisse (SIA 261)",
    icon: "pulse",
    layout: "split",
    fields: [
      {
        key: "country",
        label: "Pays / norme",
        type: "select",
        options: SEISME_COUNTRIES,
        defaultValue: "FR",
      },
      {
        key: "zone",
        label: "Zone sismique",
        type: "select",
        options: SEISME_ZONES,
        dependsOn: "country",
        defaultValue: "2",
      },
      {
        key: "soil_class",
        label: "Classe de sol",
        type: "select",
        options: SEISME_SOIL_CLASSES,
        dependsOn: "country",
        defaultValue: "C",
      },
      {
        key: "importance_class",
        label: "Catégorie d'importance",
        type: "select",
        options: SEISME_IMPORTANCE_CLASSES,
        dependsOn: "country",
        defaultValue: "II",
      },
      {
        key: "q",
        label: "Coefficient de comportement q",
        type: "number",
        defaultValue: "1.5",
        placeholder: "1.5",
      },
      {
        key: "t_point",
        label: "Période T — lecture ponctuelle",
        unit: "s",
        type: "number",
        defaultValue: "",
        placeholder: "ex. 0.5",
      },
      {
        key: "xi_percent",
        label: "Amortissement visqueux ξ",
        unit: "%",
        type: "number",
        defaultValue: "5",
        advanced: true,
      },
    ],
  },
];

export const getModule = (id: string) => MODULES.find((m) => m.id === id);
export const getCategoryModules = (cat: CategoryId) =>
  MODULES.filter((m) => m.categoryId === cat);
