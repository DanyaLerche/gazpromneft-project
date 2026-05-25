export const typography = {
  family: {
    sans: "'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
  },
  scale: {
    display: {
      size: '44px',
      lineHeight: '52px',
      weight: 800
    },
    h1: {
      size: '32px',
      lineHeight: '40px',
      weight: 700
    },
    h2: {
      size: '24px',
      lineHeight: '32px',
      weight: 700
    },
    h3: {
      size: '20px',
      lineHeight: '28px',
      weight: 700
    },
    title: {
      size: '16px',
      lineHeight: '24px',
      weight: 600
    },
    body: {
      size: '14px',
      lineHeight: '22px',
      weight: 500
    },
    bodySm: {
      size: '13px',
      lineHeight: '20px',
      weight: 500
    },
    caption: {
      size: '12px',
      lineHeight: '16px',
      weight: 600
    }
  }
} as const;

export type AppTypography = typeof typography;
