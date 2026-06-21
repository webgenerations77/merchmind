import { useEffect, useState, useCallback } from 'react';
import { useReviewStore } from '../stores/reviewStore';
import { getDesign, getReviewQueue } from '../api/designs';
import { listBatches, triggerBatch } from '../api/batches';
import { listProducts } from '../api/products';
import { getApiBalance, type ApiBalanceResult } from '../api/health';
import ClickableImage from '../components/shared/ClickableImage';
import type { DesignOut, DesignQueueItem, BatchOut, ProductOut } from '../types/api';
import ConfidenceBadge from '../components/shared/ConfidenceBadge';
import StatusBadge from '../components/shared/StatusBadge';
import { formatCurrency, formatProductType } from '../utils/formatters';
import { calculateCostBreakdown } from '../utils/profitCalc';

function BatchProgress({ batch, productCount, designCount }: { batch: BatchOut; productCount: number; designCount: number }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const start = new Date(batch.run_started_at).getTime();
    setElapsed(Math.floor((Date.now() - start) / 1000));
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [batch.run_started_at]);

  const totalDesigns = batch.queued_count || 1;
  const designsDone = designCount;
  const progressPct = batch.queued_count > 0
    ? Math.min(95, ((designsDone / totalDesigns) * 80) + (batch.total_ideas > 0 ? 10 : 0) + (batch.queued_count > 0 ? 10 : 0))
    : batch.total_ideas > 0 ? 15 : 5;

  const steps = [
    { label: 'Scraping trends', detail: batch.total_ideas > 0 ? `${batch.total_ideas} found` : '', done: batch.total_ideas > 0 },
    { label: 'Scoring & filtering', detail: batch.queued_count > 0 ? `${batch.queued_count} qualified` : '', done: batch.queued_count > 0 },
    { label: 'Generating designs', detail: batch.queued_count > 0 ? `${designsDone}/${totalDesigns}` : '', done: designsDone >= totalDesigns && totalDesigns > 0 },
    { label: 'Creating products', detail: productCount > 0 ? `${productCount} created` : '', done: productCount > 0 && designsDone >= totalDesigns },
    { label: 'Marketing copy', detail: '', done: batch.status === 'complete' },
  ];

  const currentStep = steps.findIndex((s) => !s.done);

  const formatTime = (s: number) => {
    if (s < 60) return `${s}s`;
    return `${Math.floor(s / 60)}m ${s % 60}s`;
  };

  return (
    <div className="bg-bg-secondary border border-accent/30 rounded-xl p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-accent animate-pulse" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Batch Running</h3>
            <p className="text-xs text-text-secondary">
              {formatTime(elapsed)} elapsed
              {designsDone > 0 && ` · ${designsDone}/${totalDesigns} designs`}
              {productCount > 0 && ` · ${productCount} products`}
            </p>
          </div>
        </div>
        <StatusBadge status={batch.status} />
      </div>

      <div className="w-full bg-bg-tertiary rounded-full h-2 mb-4">
        <div
          className="bg-accent rounded-full h-2 transition-all duration-1000"
          style={{ width: `${Math.max(3, progressPct)}%` }}
        />
      </div>

      <div className="grid grid-cols-5 gap-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
              step.done ? 'bg-approve/20 text-approve' :
              i === currentStep ? 'bg-accent/20 text-accent' :
              'bg-bg-tertiary text-text-tertiary'
            }`}>
              {step.done ? '✓' : i + 1}
            </span>
            <div>
              <span className={`text-xs ${step.done ? 'text-text-secondary' : i === currentStep ? 'text-accent' : 'text-text-tertiary'}`}>
                {step.label}
              </span>
              {step.detail && (
                <span className={`text-xs ml-1 ${i === currentStep ? 'text-accent font-medium' : 'text-text-tertiary'}`}>
                  {step.detail}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BatchComplete({ batch, onRefresh }: { batch: BatchOut; onRefresh: () => void }) {
  return (
    <div className="bg-bg-secondary border border-approve/30 rounded-xl p-5 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-approve text-lg">✓</span>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Batch Complete</h3>
            <p className="text-xs text-text-secondary">
              {batch.queued_count} designs generated · {batch.total_ideas} trends scored
            </p>
          </div>
        </div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/80 transition-colors">
          Load Designs
        </button>
      </div>
    </div>
  );
}

function DesignCard({ item, action, onClick }: { item: DesignQueueItem; action?: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="bg-bg-secondary border border-border rounded-xl p-4 text-left hover:border-accent/50 transition-colors w-full"
    >
      {item.processed_image_url ? (
        <ClickableImage src={item.processed_image_url} alt={item.concept_name} className="w-full h-40 object-cover rounded-lg mb-3" />
      ) : (
        <div className="w-full h-40 bg-bg-tertiary rounded-lg mb-3 flex items-center justify-center text-text-tertiary text-sm">
          Text Only
        </div>
      )}
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-text-primary truncate">{item.concept_name}</h3>
        <ConfidenceBadge score={item.quality_score} />
      </div>
      <div className="flex items-center gap-2 mb-2">
        <p className="text-xs text-text-tertiary">{item.archetype.replace(/_/g, ' ')}</p>
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
          item.classification === 'collection'
            ? 'bg-purple-500/20 text-purple-400'
            : 'bg-accent/20 text-accent'
        }`}>
          {item.classification === 'collection' ? 'Collection' : 'Design Idea'}
        </span>
        {(item.revisit_count ?? 0) > 0 && (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase bg-blue-500/20 text-blue-400">
            Revisit {item.revisit_count! > 1 ? `x${item.revisit_count}` : ''}
          </span>
        )}
      </div>
      {item.shopify_title && (
        <p className="text-xs text-text-secondary truncate">{item.shopify_title}</p>
      )}
      {action && (
        <div className="mt-2">
          <StatusBadge status={action} />
        </div>
      )}
    </button>
  );
}

function DesignDetail({ design, onBack, onApprove, onReject, onArchive, onRevisit, onDelay }: {
  design: DesignOut;
  onBack: () => void;
  onApprove: (productTypes?: string[]) => void;
  onReject: () => void;
  onArchive: () => void;
  onRevisit: () => void;
  onDelay: () => void;
}) {
  const [products, setProducts] = useState<ProductOut[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>('design');
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [selectedPublishTypes, setSelectedPublishTypes] = useState<Set<string>>(new Set());

  const clothingOrder = ['tshirt', 'hat', 'mug', 'phone_case', 'poster', 'sticker'];

  useEffect(() => {
    listProducts().then((all) => {
      const matched = all.filter((p) => p.design_id === design.id);
      setProducts(matched);
      setSelectedPublishTypes(new Set(matched.map((p) => p.product_type)));
      const withMockups = matched.filter((p) => p.mockup_urls && Object.keys(p.mockup_urls).length > 0);
      const clothing = withMockups.find((p) => clothingOrder.indexOf(p.product_type) <= 1);
      const defaultMockup = clothing || withMockups[0];
      if (defaultMockup) setSelectedProduct(defaultMockup.id);
    }).catch(() => null);
  }, [design.id]);

  const productsWithMockups = products
    .filter((p) => p.mockup_urls && Object.keys(p.mockup_urls).length > 0)
    .sort((a, b) => clothingOrder.indexOf(a.product_type) - clothingOrder.indexOf(b.product_type));
  const viewOptions = [
    ...productsWithMockups.map((p) => ({ key: p.id, label: formatProductType(p.product_type) })),
    { key: 'design', label: 'Original Design' },
  ];

  const currentMockup = selectedProduct === 'design'
    ? null
    : productsWithMockups.find((p) => p.id === selectedProduct);

  return (
    <div>
      <button onClick={onBack} className="text-text-secondary hover:text-text-primary text-sm mb-4">
        &larr; Back to queue
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
          ) : design.processed_image_url ? (
            <ClickableImage src={design.processed_image_url} alt={design.concept_name} className="w-full rounded-xl" />
          ) : (
            <div className="w-full h-64 bg-bg-tertiary rounded-xl flex items-center justify-center text-text-tertiary">
              Text Only Design
            </div>
          )}
          {design.image_api_used && (
            <p className="text-xs text-text-tertiary mt-2">Generated via {design.image_api_used}</p>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-bold text-text-primary">{design.concept_name}</h2>
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
          </div>

          {products.length > 0 && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-2">Products ({products.length})</p>
              <div className="space-y-2">
                {products.map((p) => {
                  const b = calculateCostBreakdown(p.retail_price, p.printify_base_cost);
                  return (
                    <div key={p.id} className="flex items-center justify-between">
                      <span className="text-sm text-text-primary">{formatProductType(p.product_type)}</span>
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
          )}

          {design.quality_breakdown && (
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

          {design.shopify_title && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-1">Shopify Title</p>
              <p className="text-sm text-text-primary">{design.shopify_title}</p>
            </div>
          )}

          {design.shopify_description && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-1">Shopify Description</p>
              <p className="text-sm text-text-secondary whitespace-pre-line max-h-48 overflow-y-auto">{design.shopify_description}</p>
            </div>
          )}

          {design.shopify_tags && design.shopify_tags.length > 0 && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-2">Tags</p>
              <div className="flex flex-wrap gap-1">
                {design.shopify_tags.map((tag) => (
                  <span key={tag} className="px-2 py-0.5 bg-bg-tertiary rounded text-xs text-text-secondary">{tag}</span>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-4 border-t border-border">
            <button
              onClick={() => { if (confirm('Permanently delete this design and all assets? This cannot be undone.')) onReject(); }}
              className="py-2.5 px-3 rounded-lg bg-reject/20 text-reject font-semibold text-sm hover:bg-reject/30 transition-colors"
            >
              Reject
            </button>
            <button onClick={onArchive} className="py-2.5 px-3 rounded-lg bg-amber-500/20 text-amber-400 font-semibold text-sm hover:bg-amber-500/30 transition-colors">
              Archive
            </button>
            <button onClick={onRevisit} className="py-2.5 px-3 rounded-lg bg-blue-500/20 text-blue-400 font-semibold text-sm hover:bg-blue-500/30 transition-colors">
              Revisit
            </button>
            <button onClick={onDelay} className="py-2.5 px-3 rounded-lg bg-delay/20 text-delay font-semibold text-sm hover:bg-delay/30 transition-colors">
              Delay
            </button>
            <button onClick={() => setShowPublishDialog(true)} className="flex-1 py-2.5 rounded-lg bg-approve/20 text-approve font-semibold text-sm hover:bg-approve/30 transition-colors">
              Approve & Publish
            </button>
          </div>

          {showPublishDialog && (
            <div className="mt-4 p-4 bg-bg-tertiary rounded-xl border border-accent/30">
              <p className="text-sm font-semibold text-text-primary mb-3">Select products to publish:</p>
              <div className="space-y-2 mb-4">
                {products.map((p) => (
                  <label key={p.id} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPublishTypes.has(p.product_type)}
                      onChange={(e) => {
                        const next = new Set(selectedPublishTypes);
                        if (e.target.checked) next.add(p.product_type);
                        else next.delete(p.product_type);
                        setSelectedPublishTypes(next);
                      }}
                      className="w-4 h-4 rounded accent-accent"
                    />
                    <span className="text-sm text-text-primary">{formatProductType(p.product_type)}</span>
                    <span className="text-xs text-text-tertiary ml-auto">{formatCurrency(p.retail_price)}</span>
                  </label>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowPublishDialog(false)}
                  className="flex-1 py-2 rounded-lg bg-bg-secondary border border-border text-sm text-text-secondary hover:text-text-primary transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => onApprove(Array.from(selectedPublishTypes))}
                  disabled={selectedPublishTypes.size === 0}
                  className="flex-1 py-2 rounded-lg bg-approve text-white font-semibold text-sm hover:bg-approve/90 disabled:opacity-50 transition-colors"
                >
                  Publish {selectedPublishTypes.size} Product{selectedPublishTypes.size !== 1 ? 's' : ''}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReviewPage() {
  const { queue, archivedQueue, sessionActions, isLoading, error, fetchQueue, fetchArchived, approveDesign, rejectDesign, archiveDesign, unarchiveDesign, revisitDesign, delayDesign } = useReviewStore();
  const [selectedDesign, setSelectedDesign] = useState<DesignOut | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [runningBatch, setRunningBatch] = useState<BatchOut | null>(null);
  const [recentBatch, setRecentBatch] = useState<BatchOut | null>(null);
  const [productCount, setProductCount] = useState(0);
  const [batchDesignCount, setBatchDesignCount] = useState(0);
  const [triggering, setTriggering] = useState(false);
  const [apiBalance, setApiBalance] = useState<ApiBalanceResult | null>(null);
  const [balanceOverride, setBalanceOverride] = useState(false);

  const checkBatchStatus = useCallback(async () => {
    try {
      const batches = await listBatches();
      const latest = batches[0];
      if (latest?.status === 'running') {
        setRunningBatch(latest);
        setRecentBatch(null);
        const products = await listProducts();
        const batchStart = new Date(latest.run_started_at).getTime();
        const batchProducts = products.filter((p) => new Date(p.created_at).getTime() >= batchStart);
        setProductCount(batchProducts.length);
        const latestQueue = await getReviewQueue();
        setBatchDesignCount(latestQueue.filter((d) => d.source === 'batch').length);
      } else if (latest?.status === 'complete') {
        setRunningBatch((prev) => {
          if (prev) setRecentBatch(latest);
          return null;
        });
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchQueue();
    fetchArchived();
    checkBatchStatus();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!runningBatch) return;
    const interval = setInterval(checkBatchStatus, 5000);
    return () => clearInterval(interval);
  }, [runningBatch, checkBatchStatus]);

  const handleTrigger = async () => {
    const balance = await getApiBalance().catch(() => null);
    setApiBalance(balance);
    if (balance && !balance.ok && !balanceOverride) return;
    if (!confirm('Run a new batch now?')) return;
    setTriggering(true);
    try {
      await triggerBatch();
      setTimeout(checkBatchStatus, 2000);
    } catch { /* ignore */ }
    setTriggering(false);
  };

  const handleRefresh = () => {
    setRecentBatch(null);
    fetchQueue();
  };

  const [reviewTab, setReviewTab] = useState<'batch' | 'collections' | 'drews_mind' | 'archived'>('batch');

  const pending = queue.filter((d) => !sessionActions[d.id]);
  const actioned = queue.filter((d) => sessionActions[d.id]);

  const batchDesigns = pending.filter((d) => d.source === 'batch' || (!d.collection_id && !d.source));
  const drewsDesigns = pending.filter((d) => d.source === 'drews_mind');
  const collectionDesigns = pending.filter((d) => d.source === 'collection' || !!d.collection_id);
  const collectionGroups: Record<string, { name: string; designs: typeof collectionDesigns }> = {};
  for (const d of collectionDesigns) {
    const key = d.collection_id || 'ungrouped';
    if (!collectionGroups[key]) {
      collectionGroups[key] = { name: d.collection_name || 'Collection', designs: [] };
    }
    collectionGroups[key].designs.push(d);
  }

  const tabCounts = {
    batch: batchDesigns.length,
    collections: collectionDesigns.length,
    drews_mind: drewsDesigns.length,
    archived: archivedQueue.length,
  };

  const openDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const design = await getDesign(id);
      setSelectedDesign(design);
    } catch { /* ignore */ }
    setLoadingDetail(false);
  };

  const handleAction = async (action: 'approve' | 'reject' | 'archive' | 'revisit' | 'delay', id: string, productTypes?: string[]) => {
    if (action === 'approve') {
      await approveDesign(id, productTypes);
    } else if (action === 'reject') {
      await rejectDesign(id);
    } else if (action === 'archive') {
      await archiveDesign(id);
      fetchArchived();
    } else if (action === 'revisit') {
      await revisitDesign(id);
    } else {
      const nextWeek = new Date();
      nextWeek.setDate(nextWeek.getDate() + 7);
      await delayDesign(id, nextWeek.toISOString().split('T')[0]);
    }
    setSelectedDesign(null);
  };

  if (isLoading) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading queue...</div>;
  if (error) return <div className="text-confidence-low p-4">Error: {error}</div>;

  if (selectedDesign) {
    return (
      <DesignDetail
        design={selectedDesign}
        onBack={() => setSelectedDesign(null)}
        onApprove={(productTypes) => handleAction('approve', selectedDesign.id, productTypes)}
        onReject={() => handleAction('reject', selectedDesign.id)}
        onArchive={() => handleAction('archive', selectedDesign.id)}
        onRevisit={() => handleAction('revisit', selectedDesign.id)}
        onDelay={() => handleAction('delay', selectedDesign.id)}
      />
    );
  }

  if (loadingDetail) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading design...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Review Queue</h1>
          <p className="text-sm text-text-secondary mt-1">
            {pending.length} designs pending review
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchQueue} className="px-3 py-1.5 rounded-lg bg-bg-secondary border border-border text-sm text-text-secondary hover:text-text-primary transition-colors">
            Refresh
          </button>
          {!runningBatch && (
            <button
              onClick={handleTrigger}
              disabled={triggering}
              className="px-3 py-1.5 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/80 transition-colors disabled:opacity-50"
            >
              {triggering ? 'Starting...' : 'Run Batch'}
            </button>
          )}
        </div>
      </div>

      {apiBalance && !apiBalance.ok && !balanceOverride && (
        <div className="bg-confidence-low/10 border border-confidence-low/30 rounded-xl p-4 mb-6">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-sm font-semibold text-confidence-low">API Balance Warning</h3>
              <p className="text-xs text-text-secondary mt-1">One or more API services may be low on credits:</p>
              <div className="flex gap-3 mt-2">
                {Object.values(apiBalance.services).map((svc) => (
                  <span key={svc.service} className={`text-xs font-medium ${svc.ok ? 'text-approve' : 'text-confidence-low'}`}>
                    {svc.service}: {svc.ok ? 'OK' : svc.error || 'Issue'}
                  </span>
                ))}
              </div>
            </div>
            <button
              onClick={() => { setBalanceOverride(true); handleTrigger(); }}
              className="px-3 py-1.5 rounded-lg bg-confidence-low/20 text-confidence-low text-xs font-medium hover:bg-confidence-low/30 transition-colors shrink-0"
            >
              Continue Anyway
            </button>
          </div>
        </div>
      )}

      {runningBatch && <BatchProgress batch={runningBatch} productCount={productCount} designCount={batchDesignCount} />}
      {recentBatch && <BatchComplete batch={recentBatch} onRefresh={handleRefresh} />}

      <div className="flex gap-1 mb-6 bg-bg-secondary rounded-lg p-1 border border-border">
        {([['batch', 'Design Ideas'], ['collections', 'Collections'], ['drews_mind', "Drew's Mind"], ['archived', 'Archived']] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setReviewTab(key)}
            className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              reviewTab === key ? 'bg-accent text-white' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {label} {tabCounts[key] > 0 && <span className="ml-1 text-xs opacity-75">({tabCounts[key]})</span>}
          </button>
        ))}
      </div>

      {reviewTab === 'batch' && (
        batchDesigns.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {batchDesigns.map((item) => (
              <DesignCard key={item.id} item={item} onClick={() => openDetail(item.id)} />
            ))}
          </div>
        ) : (
          <div className="text-center py-16 text-text-tertiary">
            <p className="text-lg">No batch designs to review</p>
            <p className="text-sm mt-1">Click "Run Batch" to generate designs from trending topics</p>
          </div>
        )
      )}

      {reviewTab === 'collections' && (
        Object.keys(collectionGroups).length > 0 ? (
          Object.entries(collectionGroups).map(([collectionId, group]) => (
            <div key={collectionId} className="mb-8">
              <div className="flex items-center gap-3 mb-3">
                <h2 className="text-lg font-semibold text-text-primary">{group.name}</h2>
                <span className="text-xs text-text-tertiary bg-bg-tertiary px-2 py-0.5 rounded-full">
                  {group.designs.length} designs
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {group.designs.map((item) => (
                  <DesignCard key={item.id} item={item} onClick={() => openDetail(item.id)} />
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-16 text-text-tertiary">
            <p className="text-lg">No collection designs to review</p>
            <p className="text-sm mt-1">Create a collection and generate designs from the Collections page</p>
          </div>
        )
      )}

      {reviewTab === 'drews_mind' && (
        drewsDesigns.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {drewsDesigns.map((item) => (
              <DesignCard key={item.id} item={item} onClick={() => openDetail(item.id)} />
            ))}
          </div>
        ) : (
          <div className="text-center py-16 text-text-tertiary">
            <p className="text-lg">No Drew's Mind designs to review</p>
            <p className="text-sm mt-1">Create ideas from the Drew's Mind page</p>
          </div>
        )
      )}

      {reviewTab === 'archived' && (
        archivedQueue.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {archivedQueue.map((item) => (
              <div key={item.id} className="relative">
                <DesignCard item={item} onClick={() => openDetail(item.id)} />
                <button
                  onClick={async (e) => { e.stopPropagation(); await unarchiveDesign(item.id); }}
                  className="absolute top-2 right-2 px-2 py-1 rounded-lg bg-approve/20 text-approve text-xs font-semibold hover:bg-approve/30 transition-colors"
                >
                  Unarchive
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 text-text-tertiary">
            <p className="text-lg">No archived designs</p>
            <p className="text-sm mt-1">Archived designs will appear here</p>
          </div>
        )
      )}

      {actioned.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-text-primary mb-3">Reviewed this session</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {actioned.map((item) => (
              <DesignCard
                key={item.id}
                item={item}
                action={sessionActions[item.id]}
                onClick={() => openDetail(item.id)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
