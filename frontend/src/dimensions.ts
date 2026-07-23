const DIMENSION_LABELS: Record<string, string> = {
  star_structure: "STAR structure",
  specificity: "Specificity",
  voice_authenticity: "Voice authenticity",
  trajectory_signal: "Trajectory signal",
  generic_phrasing: "Generic phrasing",
};

export function dimensionLabel(dimension: string): string {
  return DIMENSION_LABELS[dimension] || dimension.replace(/_/g, " ");
}
