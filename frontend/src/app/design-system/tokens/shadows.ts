export const shadows = {
  xs: '0 1px 2px rgba(18, 24, 40, 0.05)',
  sm: '0 8px 20px rgba(15, 23, 42, 0.06)',
  md: '0 16px 36px rgba(15, 23, 42, 0.08)',
  lg: '0 22px 48px rgba(76, 55, 180, 0.12)'
} as const;

export type AppShadows = typeof shadows;
