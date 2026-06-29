import { useState, useEffect } from 'react';
import ClickableImage from './ClickableImage';
import ColorSwatchPicker from './ColorSwatchPicker';
import { getColors } from '../../api/catalog';
import { updateProduct } from '../../api/products';
import type { ProductOut, CatalogColor } from '../../types/api';
import { formatProductType } from '../../utils/formatters';

const PRODUCT_ORDER = ['tshirt', 'hoodie', 'long_sleeve'];

// Blueprint/provider per product type (mirrors backend _BLUEPRINT_MAP/_PROVIDER_MAP;
// used only to request the right swatch set — backend stays source of truth).
const BLUEPRINT_PROVIDER: Record<string, { bp: number; prov: number }> = {
  tshirt: { bp: 5, prov: 99 },
  hoodie: { bp: 77, prov: 99 },
  long_sleeve: { bp: 41, prov: 99 },
};

interface MockupTabsProps {
  products: ProductOut[];
  designImageUrl: string | null;
  designName: string;
  defaultProductType?: string | null;
  imageApiUsed?: string | null;
  primaryProductTypeReasoning?: string | null;
}

export default function MockupTabs({ products, designImageUrl, designName, defaultProductType, imageApiUsed, primaryProductTypeReasoning }: MockupTabsProps) {
  const [selectedProduct, setSelectedProduct] = useState<string>('design');

  const productsWithMockups = products
    .filter((p) => p.mockup_urls && Object.keys(p.mockup_urls).length > 0)
    .sort((a, b) => PRODUCT_ORDER.indexOf(a.product_type) - PRODUCT_ORDER.indexOf(b.product_type));

  const primaryLabel = defaultProductType ? formatProductType(defaultProductType) : null;

  const viewOptions = [
    ...productsWithMockups.map((p) => ({
      key: p.id,
      label: formatProductType(p.product_type),
      isPrimary: p.product_type === defaultProductType,
    })),
    { key: 'design', label: 'Original Design', isPrimary: false },
  ];

  useEffect(() => {
    const primary = defaultProductType
      ? productsWithMockups.find((p) => p.product_type === defaultProductType)
      : null;
    const defaultMockup = primary || productsWithMockups[0];
    if (defaultMockup) setSelectedProduct(defaultMockup.id);
  }, [products.length]);

  const currentMockup = selectedProduct === 'design'
    ? null
    : productsWithMockups.find((p) => p.id === selectedProduct);

  const [colors, setColors] = useState<CatalogColor[]>([]);
  const [selectedColor, setSelectedColor] = useState<string | null>(null);
  const [colorLoading, setColorLoading] = useState(false);

  useEffect(() => {
    if (!currentMockup) { setColors([]); return; }
    setSelectedColor(currentMockup.selected_color ?? null);
    const bpProv = BLUEPRINT_PROVIDER[currentMockup.product_type];
    if (!bpProv) { setColors([]); return; }
    getColors(bpProv.bp, bpProv.prov)
      .then((cs) => {
        setColors(cs);
        if (!currentMockup.selected_color && cs.length) setSelectedColor(cs[0].name);
      })
      .catch(() => setColors([]));
  }, [selectedProduct]);

  const handleColorSelect = async (colorName: string) => {
    if (!currentMockup) return;
    setColorLoading(true);
    setSelectedColor(colorName); // optimistic
    try {
      await updateProduct(currentMockup.id, { selected_color: colorName });
    } finally {
      setColorLoading(false);
    }
  };

  const colorMockupUrl = currentMockup && selectedColor
    ? (currentMockup.color_mockups?.[selectedColor] || currentMockup.mockup_urls['front'])
    : undefined;

  return (
    <div>
      {viewOptions.length > 1 && (
        <div className="flex gap-2 mb-3 flex-wrap">
          {viewOptions.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setSelectedProduct(opt.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedProduct === opt.key
                  ? 'bg-accent text-white'
                  : 'bg-bg-secondary text-text-secondary hover:text-text-primary border border-border'
              }`}
            >
              {opt.label}
              {opt.isPrimary && <span className="ml-1 opacity-75">*</span>}
            </button>
          ))}
        </div>
      )}

      {currentMockup ? (
        <div className="space-y-2">
          {colors.length > 0 && (
            <ColorSwatchPicker
              colors={colors}
              selected={selectedColor}
              onSelect={handleColorSelect}
              loading={colorLoading}
            />
          )}
          <div className={colorLoading ? 'opacity-50 transition-opacity' : 'transition-opacity'}>
            {colorMockupUrl && (
              <ClickableImage src={colorMockupUrl} alt="front mockup" className="w-full rounded-xl" />
            )}
            {currentMockup.mockup_urls['back'] && (
              <ClickableImage src={currentMockup.mockup_urls['back'] as string} alt="back mockup" className="w-full rounded-xl mt-2" />
            )}
          </div>
        </div>
      ) : designImageUrl ? (
        <div>
          <ClickableImage src={designImageUrl} alt={designName} className="w-full rounded-xl" />
          {primaryLabel && (
            <p className="text-xs text-accent mt-2">
              Designed for: <span className="font-semibold">{primaryLabel}</span>
            </p>
          )}
        </div>
      ) : (
        <div className="w-full h-64 bg-bg-tertiary rounded-xl flex items-center justify-center text-text-tertiary">
          Text Only Design
        </div>
      )}

      {imageApiUsed && (
        <p className="text-xs text-text-tertiary mt-2">Generated via {imageApiUsed}</p>
      )}

      {primaryProductTypeReasoning && selectedProduct === 'design' && (
        <div className="mt-2 p-2 bg-bg-secondary rounded-lg border border-border">
          <p className="text-[10px] text-text-tertiary uppercase font-semibold mb-1">Primary Product Reasoning</p>
          <p className="text-xs text-text-secondary">{primaryProductTypeReasoning}</p>
        </div>
      )}
    </div>
  );
}
