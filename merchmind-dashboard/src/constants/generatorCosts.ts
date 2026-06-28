// Image generator options and their costs per design (USD).
// These should stay in sync with DALLE3_COST_PER_IMAGE etc. in backend config.py.

export interface GeneratorOption {
  value: string;
  label: string;
  costPerImage: number;
  description: string;
}

export const GENERATOR_OPTIONS: GeneratorOption[] = [
  {
    value: 'flux_schnell',
    label: 'Flux Schnell',
    costPerImage: 0.003,
    description: 'Fast · Best for illustrations & flat art',
  },
  {
    value: 'dalle3',
    label: 'DALL·E 3',
    costPerImage: 0.04,
    description: 'Higher quality · Complex scenes & detail',
  },
  {
    value: 'ideogram',
    label: 'Ideogram',
    costPerImage: 0.08,
    description: 'Image + text in one call · Best for image_with_text',
  },
  {
    value: 'text_only',
    label: 'Text Only',
    costPerImage: 0.00,
    description: 'No image API · Typography & slogan designs',
  },
];

export const GENERATOR_DEFAULT_BY_ARCHETYPE: Record<string, string> = {
  illustration: 'flux_schnell',
  hybrid: 'flux_schnell',
  text_icon: 'flux_schnell',
  image_with_text: 'ideogram',
  typographic: 'text_only',
  text_only: 'text_only',
};

export function getGeneratorOption(value: string): GeneratorOption | undefined {
  return GENERATOR_OPTIONS.find((g) => g.value === value);
}
