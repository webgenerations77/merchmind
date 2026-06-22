import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { listProducts, updateProduct, retryPublish } from '../api/products';
import { getDesign, retireDesign } from '../api/designs';
import type { ProductOut, DesignOut } from '../types/api';
import StatusBadge from '../components/shared/StatusBadge';
import ConfidenceBadge from '../components/shared/ConfidenceBadge';
import MockupTabs from '../components/shared/MockupTabs';
import { formatCurrency, formatProductType, formatDate, toTitleCase } from '../utils/formatters';
import { calculateCostBreakdown } from '../utils/profitCalc';

const filters = ['all', 'pending', 'live', 'published', 'failed', 'unpublished'] as const;

function ProductDetail({ product, allProducts, onBack, onUpdate }: {
  product: ProductOut;
  allProducts: ProductOut[];
  onBack: () => void;
  onUpdate: (products: ProductOut[]) => void;
}) {
  const [design, setDesign] = useState<DesignOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [retireError, setRetireError] = useState<string | null>(null);

  const designProducts = allProducts.filter((p) => p.design_id === product.design_id);

  useEffect(() => {
    getDesign(product.design_id).then(setDesign).catch(() => null).finally(() => setLoading(false));
  }, [product.design_id]);

  const hasLiveProducts = designProducts.some((p) => p.publish_status === 'live' || p.publish_status === 'printify_only');
  const allRetired = designProducts.every((p) => p.publish_status === 'retired');

  const handleRetire = async () => {
    if (!confirm('Retire all products for this design? They will be unpublished from Shopify but records are preserved.')) return;
    setActionLoading(true);
    setRetireError(null);
    try {
      const result = await retireDesign(product.design_id);
      if (result.failed.length > 0) {
        setRetireError(`Failed to retire: ${result.failed.map((f) => `${formatProductType(f.type)} (${f.error.slice(0, 60)})`).join(', ')}`);
      }
      const retiredTypes = new Set(result.retired);
      const updated = allProducts.map((p) => {
        if (p.design_id === product.design_id && retiredTypes.has(p.product_type)) {
          return { ...p, publish_status: 'retired', unpublished_at: new Date().toISOString() };
        }
        return p;
      });
      onUpdate(updated);
    } catch {
      setRetireError('Failed to retire products. Please try again.');
    }
    setActionLoading(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading design...</div>;

  return (
    <div>
      <button onClick={onBack} className="text-text-secondary hover:text-text-primary text-sm mb-4">
        &larr; Back to products
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MockupTabs
          products={designProducts}
          designImageUrl={design?.processed_image_url ?? null}
          designName={design?.concept_name ?? product.product_type}
          defaultProductType={product.product_type}
          imageApiUsed={design?.image_api_used}
        />

        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-text-primary">
                {design ? toTitleCase(design.concept_name) : formatProductType(product.product_type)}
              </h2>
              {allRetired && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-semibold uppercase bg-text-tertiary/20 text-text-tertiary">Retired</span>
              )}
            </div>
            {design && (
              <div className="flex items-center gap-2 mt-2">
                <ConfidenceBadge score={design.quality_score} />
                <StatusBadge status={design.archetype} />
                <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                  design.classification === 'collection'
                    ? 'bg-purple-500/20 text-purple-400'
                    : 'bg-accent/20 text-accent'
                }`}>
                  {design.classification === 'collection' ? 'Collection' : 'Design Idea'}
                </span>
                {design.version > 1 && <span className="text-xs text-text-tertiary">v{design.version}</span>}
              </div>
            )}
          </div>

          <div className="p-3 bg-bg-secondary rounded-lg border border-border">
            <p className="text-xs text-text-tertiary mb-2">Products ({designProducts.length})</p>
            <div className="space-y-2">
              {designProducts.map((p) => {
                const b = calculateCostBreakdown(p.retail_price, p.printify_base_cost);
                return (
                  <div key={p.id} className={`flex items-center justify-between ${p.publish_status === 'retired' ? 'opacity-50' : ''}`}>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-text-primary">{formatProductType(p.product_type)}</span>
                      <StatusBadge status={p.publish_status} />
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-text-tertiary">COGS {formatCurrency(b.totalCogs)}</span>
                      <span className="text-xs text-approve">Net {formatCurrency(b.netProfit)}</span>
                      <span className={`text-xs font-medium ${b.netMargin >= 30 ? 'text-approve' : 'text-confidence-medium'}`}>{b.netMargin.toFixed(0)}%</span>
                      <span className="text-sm font-medium text-accent">{formatCurrency(p.retail_price)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {design?.quality_breakdown && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-2">Quality Breakdown</p>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(design.quality_breakdown).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-xs text-text-secondary capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="text-xs font-semibold text-text-primary">{val}/10</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {design?.shopify_title && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-1">Shopify Title</p>
              <p className="text-sm text-text-primary">{design.shopify_title}</p>
            </div>
          )}

          {design?.shopify_description && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-1">Shopify Description</p>
              <p className="text-sm text-text-secondary whitespace-pre-line max-h-48 overflow-y-auto">{design.shopify_description}</p>
            </div>
          )}

          {design?.shopify_tags && design.shopify_tags.length > 0 && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-2">Tags</p>
              <div className="flex flex-wrap gap-1">
                {design.shopify_tags.map((tag) => (
                  <span key={tag} className="px-2 py-0.5 bg-bg-tertiary rounded text-xs text-text-secondary">{tag}</span>
                ))}
              </div>
            </div>
          )}

          <div className="bg-bg-secondary border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Details</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">Design ID</span>
                <span className="text-text-tertiary font-mono text-xs">{product.design_id.slice(0, 8)}</span>
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
              {product.unpublished_at && (
                <div className="flex justify-between">
                  <span className="text-text-secondary">Retired</span>
                  <span className="text-text-primary">{formatDate(product.unpublished_at)}</span>
                </div>
              )}
            </div>
          </div>

          <div className="bg-bg-secondary border border-border rounded-xl p-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Actions</h3>
            <div className="space-y-2">
              {hasLiveProducts && !allRetired && (
                <button
                  disabled={actionLoading}
                  onClick={handleRetire}
                  className="w-full py-2.5 rounded-lg bg-text-tertiary/15 text-text-secondary font-semibold text-sm hover:bg-text-tertiary/25 transition-colors disabled:opacity-50"
                >
                  {actionLoading ? 'Retiring...' : 'Retire Product'}
                </button>
              )}
              {!hasLiveProducts && !allRetired && designProducts.some((p) => p.publish_status === 'pending') && (
                <button
                  disabled={actionLoading}
                  onClick={async () => {
                    setActionLoading(true);
                    try {
                      const updated = await updateProduct(product.id, { publish_status: 'unpublished' });
                      onUpdate(allProducts.map((x) => x.id === updated.id ? updated : x));
                    } catch { /* ignore */ }
                    setActionLoading(false);
                  }}
                  className="w-full py-2 rounded-lg bg-bg-tertiary border border-border text-sm text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
                >
                  Cancel (set to Unpublished)
                </button>
              )}
              {designProducts.some((p) => p.publish_status === 'failed') && (
                <button
                  disabled={actionLoading}
                  onClick={async () => {
                    setActionLoading(true);
                    try {
                      const failedProduct = designProducts.find((p) => p.publish_status === 'failed')!;
                      await retryPublish(failedProduct.id);
                      onUpdate(allProducts.map((x) => x.id === failedProduct.id ? { ...x, publish_status: 'pending' } : x));
                    } catch { /* ignore */ }
                    setActionLoading(false);
                  }}
                  className="w-full py-2 rounded-lg bg-accent/15 text-accent text-sm font-medium hover:bg-accent/25 transition-colors disabled:opacity-50"
                >
                  Retry Failed Publish
                </button>
              )}

              {retireError && (
                <div className="p-2 rounded-lg bg-confidence-low/10 border border-confidence-low/30">
                  <p className="text-xs text-confidence-low">{retireError}</p>
                </div>
              )}

              {allRetired && (
                <div className="p-3 rounded-lg bg-text-tertiary/10 border border-border">
                  <p className="text-xs text-text-tertiary text-center">All products have been retired</p>
                </div>
              )}
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
  const [showRetired, setShowRetired] = useState(false);
  const [sortKey, setSortKey] = useState<'created_at' | 'retail_price' | 'product_type'>('created_at');
  const [selected, setSelected] = useState<ProductOut | null>(null);
  const location = useLocation();

  const loadProducts = () => {
    setLoading(true);
    listProducts(undefined, showRetired).then((p) => {
      setProducts(p);
      const navState = location.state as { selectedId?: string } | null;
      if (navState?.selectedId) {
        const match = p.find((prod) => prod.id === navState.selectedId);
        if (match) setSelected(match);
      }
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    loadProducts();
  }, [showRetired, location.state]);

  if (selected) {
    return <ProductDetail
      product={selected}
      allProducts={products}
      onBack={() => { setSelected(null); loadProducts(); }}
      onUpdate={(updated) => {
        setProducts(updated);
        const refreshed = updated.find((p) => p.id === selected.id);
        if (refreshed) setSelected(refreshed);
      }}
    />;
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
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showRetired}
              onChange={(e) => setShowRetired(e.target.checked)}
              className="w-4 h-4 rounded accent-accent"
            />
            <span className="text-sm text-text-secondary">Show Retired</span>
          </label>
          <p className="text-sm text-text-secondary">{products.length} total</p>
        </div>
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
        {showRetired && (
          <button
            onClick={() => setFilter('retired')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === 'retired' ? 'bg-accent text-white' : 'bg-bg-secondary text-text-secondary hover:text-text-primary border border-border'
            }`}
          >
            Retired ({products.filter((p) => p.publish_status === 'retired').length})
          </button>
        )}
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
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">COGS</th>
              <th className="text-left px-4 py-3 text-xs text-text-tertiary font-medium">Net Profit</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((product) => {
              const b = calculateCostBreakdown(product.retail_price, product.printify_base_cost);
              const isRetired = product.publish_status === 'retired';
              return (
                <tr
                  key={product.id}
                  onClick={() => setSelected(product)}
                  className={`border-b border-border last:border-b-0 hover:bg-bg-tertiary/50 cursor-pointer ${isRetired ? 'opacity-40' : ''}`}
                >
                  <td className="px-4 py-3 text-sm text-text-primary">{formatProductType(product.product_type)}</td>
                  <td className="px-4 py-3 text-sm text-text-primary font-medium">{formatCurrency(product.retail_price)}</td>
                  <td className="px-4 py-3 text-sm text-text-secondary">{formatDate(product.created_at)}</td>
                  <td className="px-4 py-3"><StatusBadge status={product.publish_status} /></td>
                  <td className="px-4 py-3 text-sm text-text-tertiary">{formatCurrency(b.totalCogs)}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={b.netProfit > 0 ? 'text-approve' : 'text-confidence-low'}>
                      {formatCurrency(b.netProfit)}
                    </span>
                    <span className={`ml-1 text-xs ${b.netMargin >= 30 ? 'text-approve' : 'text-confidence-medium'}`}>
                      {b.netMargin.toFixed(0)}%
                    </span>
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
