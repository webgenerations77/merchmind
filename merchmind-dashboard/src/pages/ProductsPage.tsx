import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { listProducts } from '../api/products';
import { getDesign } from '../api/designs';
import type { ProductOut, DesignOut } from '../types/api';
import StatusBadge from '../components/shared/StatusBadge';
import ConfidenceBadge from '../components/shared/ConfidenceBadge';
import ClickableImage from '../components/shared/ClickableImage';
import { formatCurrency, formatProductType, formatDate } from '../utils/formatters';

const filters = ['all', 'pending', 'live', 'published', 'failed', 'unpublished'] as const;

function ProductDetail({ product, onBack }: { product: ProductOut; onBack: () => void }) {
  const [design, setDesign] = useState<DesignOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDesign(product.design_id).then(setDesign).catch(() => null).finally(() => setLoading(false));
  }, [product.design_id]);

  const baseCost = product.printify_base_cost;
  const retailPrice = product.retail_price;
  const estimatedProfit = retailPrice - baseCost;
  const marginPct = baseCost > 0 ? ((estimatedProfit / retailPrice) * 100) : 100;

  return (
    <div>
      <button onClick={onBack} className="text-text-secondary hover:text-text-primary text-sm mb-4">
        &larr; Back to products
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-bg-secondary border border-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-text-primary">{formatProductType(product.product_type)}</h2>
                {design && <p className="text-sm text-text-secondary mt-0.5">{design.concept_name}</p>}
              </div>
              <StatusBadge status={product.publish_status} />
            </div>

            {loading ? (
              <div className="h-48 flex items-center justify-center text-text-tertiary">Loading design...</div>
            ) : design ? (
              <div className="flex gap-4">
                {product.mockup_urls && Object.keys(product.mockup_urls).length > 0 ? (
                  <div className="flex gap-2 shrink-0">
                    {Object.entries(product.mockup_urls).map(([position, url]) => (
                      <ClickableImage key={position} src={url as string} alt={`${position} mockup`} className="w-48 h-48 object-cover rounded-lg" />
                    ))}
                  </div>
                ) : design.processed_image_url ? (
                  <ClickableImage src={design.processed_image_url} alt={design.concept_name} className="w-48 h-48 object-cover rounded-lg shrink-0" />
                ) : (
                  <div className="w-48 h-48 bg-bg-tertiary rounded-lg flex items-center justify-center text-text-tertiary text-sm shrink-0">
                    Text Only
                  </div>
                )}
                <div className="space-y-2 min-w-0">
                  <div className="flex items-center gap-2">
                    <ConfidenceBadge score={design.quality_score} />
                    <StatusBadge status={design.archetype} />
                    {design.version > 1 && <span className="text-xs text-text-tertiary">v{design.version}</span>}
                  </div>
                  {design.shopify_title && (
                    <p className="text-sm text-text-primary font-medium">{design.shopify_title}</p>
                  )}
                  {design.font_pair && (
                    <p className="text-xs text-text-tertiary">Font: {design.font_pair}</p>
                  )}
                  {design.shopify_tags && design.shopify_tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {design.shopify_tags.slice(0, 10).map((tag) => (
                        <span key={tag} className="px-1.5 py-0.5 bg-bg-tertiary rounded text-xs text-text-tertiary">{tag}</span>
                      ))}
                      {design.shopify_tags.length > 10 && (
                        <span className="text-xs text-text-tertiary">+{design.shopify_tags.length - 10} more</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-sm text-text-tertiary">Design not found</p>
            )}
          </div>

          {design?.shopify_description && (
            <div className="bg-bg-secondary border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-text-primary mb-2">Listing Description</h3>
              <p className="text-sm text-text-secondary whitespace-pre-line max-h-64 overflow-y-auto">{design.shopify_description}</p>
            </div>
          )}

          {design?.quality_breakdown && (
            <div className="bg-bg-secondary border border-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-text-primary mb-3">Quality Breakdown</h3>
              <div className="space-y-2">
                {Object.entries(design.quality_breakdown).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-xs text-text-secondary capitalize w-32">{key.replace(/_/g, ' ')}</span>
                    <div className="flex-1 bg-bg-tertiary rounded-full h-2">
                      <div
                        className="bg-accent rounded-full h-2 transition-all"
                        style={{ width: `${(val / 10) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-text-primary w-8 text-right">{val}/10</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-bg-secondary border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-4">Pricing Breakdown</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-text-secondary">Base Cost</span>
                <span className="text-sm text-text-primary">{formatCurrency(baseCost)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-text-secondary">Markup ({product.base_markup}x)</span>
                <span className="text-sm text-text-primary">{formatCurrency(baseCost * product.base_markup)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-text-secondary">Trend Adjustment</span>
                <span className="text-sm text-text-primary">+{formatCurrency(product.trend_adjustment)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-text-secondary">Floor Price</span>
                <span className="text-sm text-text-tertiary">{formatCurrency(product.floor_price)}</span>
              </div>
              <div className="border-t border-border pt-3 flex justify-between">
                <span className="text-sm font-semibold text-text-primary">Retail Price</span>
                <span className="text-sm font-bold text-accent">{formatCurrency(retailPrice)}</span>
              </div>
            </div>
          </div>

          <div className="bg-bg-secondary border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-4">Estimated P&L (per unit)</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-text-secondary">Revenue</span>
                <span className="text-sm text-approve">{formatCurrency(retailPrice)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-text-secondary">COGS</span>
                <span className="text-sm text-confidence-low">-{formatCurrency(baseCost)}</span>
              </div>
              <div className="border-t border-border pt-3 flex justify-between">
                <span className="text-sm font-semibold text-text-primary">Profit</span>
                <span className={`text-sm font-bold ${estimatedProfit > 0 ? 'text-approve' : 'text-confidence-low'}`}>
                  {formatCurrency(estimatedProfit)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-text-secondary">Margin</span>
                <span className={`text-sm font-semibold ${marginPct >= 40 ? 'text-approve' : marginPct >= 20 ? 'text-confidence-medium' : 'text-confidence-low'}`}>
                  {marginPct.toFixed(1)}%
                </span>
              </div>
              {product.margin_flag && (
                <div className="mt-2 p-2 bg-confidence-low/10 rounded-lg">
                  <p className="text-xs text-confidence-low font-medium">Low margin warning</p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-bg-secondary border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Details</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">Product ID</span>
                <span className="text-text-tertiary font-mono text-xs">{product.id.slice(0, 8)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Created</span>
                <span className="text-text-primary">{formatDate(product.created_at)}</span>
              </div>
              {product.published_at && (
                <div className="flex justify-between">
                  <span className="text-text-secondary">Published</span>
                  <span className="text-text-primary">{formatDate(product.published_at)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-text-secondary">Printify ID</span>
                <span className="text-text-tertiary text-xs">{product.printify_product_id || 'Not published'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProductsPage() {
  const [products, setProducts] = useState<ProductOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [sortKey, setSortKey] = useState<'created_at' | 'retail_price' | 'product_type'>('created_at');
  const [selected, setSelected] = useState<ProductOut | null>(null);
  const location = useLocation();

  useEffect(() => {
    listProducts().then((p) => {
      setProducts(p);
      const navState = location.state as { selectedId?: string } | null;
      if (navState?.selectedId) {
        const match = p.find((prod) => prod.id === navState.selectedId);
        if (match) setSelected(match);
      }
    }).finally(() => setLoading(false));
  }, [location.state]);

  if (selected) {
    return <ProductDetail product={selected} onBack={() => setSelected(null)} />;
  }

  const filtered = filter === 'all' ? products : products.filter((p) => p.publish_status === filter);
  const sorted = [...filtered].sort((a, b) => {
    if (sortKey === 'retail_price') return b.retail_price - a.retail_price;
    if (sortKey === 'product_type') return a.product_type.localeCompare(b.product_type);
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  if (loading) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-text-primary">Products</h1>
        <p className="text-sm text-text-secondary">{products.length} total</p>
      </div>

      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === f ? 'bg-accent text-white' : 'bg-bg-secondary text-text-secondary hover:text-text-primary border border-border'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f !== 'all' && ` (${products.filter((p) => p.publish_status === f).length})`}
          </button>
        ))}
      </div>

      <div className="bg-bg-secondary border border-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              {[
                { key: 'product_type', label: 'Type' },
                { key: 'retail_price', label: 'Price' },
                { key: 'created_at', label: 'Created' },
              ].map((col) => (
                <th
                  key={col.key}
                  onClick={() => setSortKey(col.key as typeof sortKey)}
                  className="text-left px-4 py-3 text-xs text-text-tertiary font-medium cursor-pointer hover:text-text-primary"
                >
                  {col.label} {sortKey === col.key && '↓'}
                </th>
              ))}
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Status</th>
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Markup</th>
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Est. Profit</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((product) => {
              const profit = product.retail_price - product.printify_base_cost;
              return (
                <tr
                  key={product.id}
                  onClick={() => setSelected(product)}
                  className="border-b border-border last:border-b-0 hover:bg-bg-tertiary/50 cursor-pointer"
                >
                  <td className="px-4 py-3 text-sm text-text-primary">{formatProductType(product.product_type)}</td>
                  <td className="px-4 py-3 text-sm text-text-primary font-medium">{formatCurrency(product.retail_price)}</td>
                  <td className="px-4 py-3 text-sm text-text-secondary">{formatDate(product.created_at)}</td>
                  <td className="px-4 py-3"><StatusBadge status={product.publish_status} /></td>
                  <td className="px-4 py-3 text-sm text-text-secondary">{product.base_markup}x</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={profit > 0 ? 'text-approve' : 'text-confidence-low'}>
                      {formatCurrency(profit)}
                    </span>
                    {product.margin_flag && <span className="ml-1 text-xs text-confidence-low">!</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <div className="p-8 text-center text-text-tertiary text-sm">No products found</div>
        )}
      </div>
    </div>
  );
}
