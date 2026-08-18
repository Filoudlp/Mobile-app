// Design tokens for C-Lab — Dark-First Utility (CAD-inspired).
// Sourced from /app/design_guidelines.json.

import { Platform } from "react-native";

export const colors = {
  surface: "#111315",
  onSurface: "#F3F4F6",
  surfaceSecondary: "#1A1D21",
  onSurfaceSecondary: "#D1D5DB",
  surfaceTertiary: "#262A2E",
  onSurfaceTertiary: "#9CA3AF",
  surfaceInverse: "#F9FAFB",
  onSurfaceInverse: "#111315",
  brand: "#E85D04",
  brandPrimary: "#E85D04",
  onBrandPrimary: "#FFFFFF",
  brandSecondary: "#F4A261",
  onBrandSecondary: "#111315",
  brandTertiary: "#4B2412",
  onBrandTertiary: "#F4A261",
  success: "#10B981",
  warning: "#F59E0B",
  error: "#EF4444",
  info: "#6B7280",
  border: "#374151",
  borderStrong: "#4B5563",
  divider: "#2D333B",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const radius = {
  sm: 4,
  md: 8,
  lg: 12,
  pill: 999,
} as const;

export const fontSize = {
  xs: 11,
  sm: 12,
  base: 14,
  lg: 16,
  xl: 20,
  xxl: 24,
  display: 32,
} as const;

// System fonts with technical / condensed feel.
// The design calls for Barlow Condensed (display) + IBM Plex Sans (text).
// We use platform defaults with weight/letter-spacing to keep parity without
// shipping font files.
export const fonts = {
  display: Platform.select({
    ios: "Helvetica Neue",
    android: "sans-serif-condensed",
    default: "System",
  }),
  text: Platform.select({
    ios: "Helvetica Neue",
    android: "sans-serif",
    default: "System",
  }),
  mono: Platform.select({
    ios: "Menlo",
    android: "monospace",
    default: "monospace",
  }),
} as const;
