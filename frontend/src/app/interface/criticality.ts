export interface JCriticality {
  id: string;
  name: string;
  level: number;
}

export function getCriticalityColor(criticality?: Pick<JCriticality, 'level'> | null): string {
  switch (criticality?.level) {
    case 1:
      return '#57A55A';
    case 2:
      return '#2D8738';
    case 3:
      return '#E97F33';
    case 4:
      return '#E9494A';
    case 5:
      return '#CD1317';
    default:
      return '#6B778C';
  }
}

export function getDefaultCriticalityId(criticalities: JCriticality[]): string | null {
  if (!criticalities.length) {
    return null;
  }

  const mediumCriticality = criticalities.find(
    (criticality) => criticality.name.toLowerCase() === 'medium'
  );
  if (mediumCriticality) {
    return mediumCriticality.id;
  }

  const sortedCriticalities = [...criticalities].sort((a, b) => a.level - b.level);
  return sortedCriticalities[Math.floor(sortedCriticalities.length / 2)]?.id ?? null;
}
