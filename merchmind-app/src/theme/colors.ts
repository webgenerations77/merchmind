export const colors = {
  bg: {
    primary: '#0A0A0A',
    secondary: '#141414',
    tertiary: '#1E1E1E',
    elevated: '#242424',
  },
  confidence: {
    high: '#22C55E',
    medium: '#EAB308',
    low: '#EF4444',
  },
  action: {
    approve: '#22C55E',
    reject: '#6B7280',
    regen: '#3B82F6',
    delay: '#A855F7',
  },
  text: {
    primary: '#F9FAFB',
    secondary: '#9CA3AF',
    tertiary: '#6B7280',
  },
  accent: '#6366F1',
  border: '#2A2A2A',
  white: '#FFFFFF',
  transparent: 'transparent',
} as const;

export type Colors = typeof colors;
