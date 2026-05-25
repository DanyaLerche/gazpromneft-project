export const colors = {
  primary: {
    500: '#6C4CF1',
    600: '#7B61FF',
    700: '#8B5CF6',
    foreground: '#FFFFFF',
    soft: 'rgba(108, 76, 241, 0.12)'
  },
  background: {
    app: '#F6F7FB',
    surface: '#FFFFFF',
    muted: '#F9FAFC',
    overlay: 'rgba(17, 24, 39, 0.52)'
  },
  text: {
    strong: '#111827',
    default: '#374151',
    muted: '#6B7280',
    subtle: '#9CA3AF'
  },
  status: {
    success: '#22C55E',
    warning: '#F59E0B',
    danger: '#EF4444',
    info: '#3B82F6'
  },
  border: {
    soft: 'rgba(0, 0, 0, 0.06)',
    strong: 'rgba(17, 24, 39, 0.12)'
  }
} as const;

export type AppColors = typeof colors;
