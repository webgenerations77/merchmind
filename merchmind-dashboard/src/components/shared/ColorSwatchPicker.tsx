import type { CatalogColor } from '../../types/api';

interface Props {
  colors: CatalogColor[];
  selected: string | null;
  onSelect: (colorName: string) => void;
  loading?: boolean;
}

export default function ColorSwatchPicker({ colors, selected, onSelect, loading }: Props) {
  if (!colors.length) return null;
  return (
    <div className="flex gap-1.5 flex-wrap items-center" role="radiogroup" aria-label="Garment color">
      {colors.map((c) => {
        const isSelected = c.name === selected;
        return (
          <button
            key={c.name}
            type="button"
            role="radio"
            aria-checked={isSelected}
            aria-label={c.name}
            title={c.name}
            disabled={loading}
            onClick={() => onSelect(c.name)}
            className={`w-6 h-6 rounded-full transition-transform hover:scale-110 disabled:opacity-50 ${
              isSelected ? 'ring-2 ring-accent ring-offset-1 ring-offset-bg-primary' : ''
            } ${c.is_light ? 'border border-border' : ''}`}
            style={{ backgroundColor: c.hex }}
          />
        );
      })}
    </div>
  );
}
