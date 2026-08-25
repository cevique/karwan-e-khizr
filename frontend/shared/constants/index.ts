// ── Karwan-e-Khizr: Shared Constants ──

// Default map center — Islamabad/Rawalpindi region
export const DEFAULT_CENTER: [number, number] = [73.0479, 33.6844]; // [lng, lat]
export const DEFAULT_ZOOM = 13;

// Islamabad/Rawalpindi bounding area
export const MAP_BOUNDS = {
  sw: { lng: 72.85, lat: 33.55 },
  ne: { lng: 73.25, lat: 33.82 },
};

// Free MapLibre-compatible style URLs (no API key required)
export const MAP_STYLE_LIGHT =
  'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
export const MAP_STYLE_DARK =
  'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

// Design tokens (shared across platforms)
export const colors = {
  light: {
    background: '#FAFAF8',
    surface: '#FFFFFF',
    surfaceElevated: '#FFFFFF',
    surfaceOverlay: 'rgba(0,0,0,0.4)',

    textPrimary: '#1A1A1A',
    textSecondary: '#5A5A5A',
    textMuted: '#9A9A9A',
    textInverse: '#FFFFFF',

    accentPrimary: '#1B8A4A',
    accentPrimaryMuted: '#E8F5EC',
    accentSecondary: '#1B3A5C',
    accentSecondaryMuted: '#E8EEF4',

    success: '#1B8A4A',
    warning: '#D4880F',
    error: '#D43D3D',

    border: '#E8E8E6',
    divider: '#F0F0EE',
    hairline: '#ECECEA',
  },
  dark: {
    background: '#000000',
    surface: '#1C1E24',
    surfaceElevated: '#24262E',
    surfaceOverlay: 'rgba(0,0,0,0.6)',

    textPrimary: '#F5F5F5',
    textSecondary: '#A0A0A0',
    textMuted: '#6A6A6A',
    textInverse: '#1A1A1A',

    accentPrimary: '#2DA65E',
    accentPrimaryMuted: '#1A2E22',
    accentSecondary: '#4A7FB5',
    accentSecondaryMuted: '#1A2430',

    success: '#2DA65E',
    warning: '#E8A020',
    error: '#E85050',

    border: '#2A2C34',
    divider: '#1E2028',
    hairline: '#22242C',
  },
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 20,
  xl: 24,
  '2xl': 32,
  '3xl': 40,
  '4xl': 48,
} as const;

export const radius = {
  small: 8,
  medium: 14,
  large: 20,
  full: 999,
} as const;

// Typography scale
export const typography = {
  display: { size: 34, lineHeight: 41, weight: '700' },
  headingLarge: { size: 28, lineHeight: 34, weight: '600' },
  headingMedium: { size: 22, lineHeight: 28, weight: '600' },
  headingSmall: { size: 17, lineHeight: 22, weight: '600' },
  bodyLarge: { size: 17, lineHeight: 24, weight: '400' },
  bodyMedium: { size: 15, lineHeight: 20, weight: '400' },
  bodySmall: { size: 13, lineHeight: 18, weight: '400' },
  labelLarge: { size: 15, lineHeight: 20, weight: '500' },
  labelMedium: { size: 13, lineHeight: 16, weight: '500' },
  labelSmall: { size: 11, lineHeight: 14, weight: '500' },
  caption: { size: 11, lineHeight: 14, weight: '400' },
} as const;
