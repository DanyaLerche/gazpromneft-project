export const motion = {
  duration: {
    fast: '150ms',
    normal: '200ms',
    slow: '250ms'
  },
  easing: {
    standard: 'cubic-bezier(0.2, 0.8, 0.2, 1)'
  }
} as const;

export type AppMotion = typeof motion;
