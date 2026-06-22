import { useState, useEffect } from 'react';
import ClickableImage from './ClickableImage';
import type { ProductOut } from '../../types/api';
import { formatProductType } from '../../utils/formatters';

const PRODUCT_ORDER = ['tshirt', 'hat', 'mug', 'phone_case', 'sticker'];

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
          {['front', 'back'].filter((pos) => currentMockup.mockup_urls[pos]).map((pos) => (
            <ClickableImage key={pos} src={currentMockup.mockup_urls[pos] as string} alt={`${pos} mockup`} className="w-full rounded-xl" />
          ))}
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
