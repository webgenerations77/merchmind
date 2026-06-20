import { useEffect, useState, useCallback } from 'react';
import { useReviewStore } from '../stores/reviewStore';
import { getDesign } from '../api/designs';
import { listBatches, triggerBatch } from '../api/batches';
import { listProducts } from '../api/products';
import ClickableImage from '../components/shared/ClickableImage';
import type { DesignOut, DesignQueueItem, BatchOut } from '../types/api';
import ConfidenceBadge from '../components/shared/ConfidenceBadge';
import StatusBadge from '../components/shared/StatusBadge';

function BatchProgress({ batch, productCount }: { batch: BatchOut; productCount: number }) {
  const startTime = new Date(batch.run_started_at).getTime();
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const estimatedProducts = batch.queued_count * 4;
  const progress = estimatedProducts > 0 ? Math.min(95, (productCount / estimatedProducts) * 100) : 0;

  const steps = [
    { label: 'Scraping trends', done: batch.total_ideas > 0 },
    { label: `Scoring ${batch.total_ideas} ideas`, done: batch.queued_count > 0 },
    { label: `Generating ${batch.queued_count} designs`, done: productCount > 0 },
    { label: 'Creating products & marketing', done: batch.status === 'complete' },
  ];

  const currentStep = steps.findIndex((s) => !s.done);

  return (
    <div className="bg-bg-secondary border border-accent/30 rounded-xl p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-accent animate-pulse" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Batch Running</h3>
            <p className="text-xs text-text-secondary">
              {elapsed < 60 ? `${elapsed}s` : `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`} elapsed
              {productCount > 0 && ` · ${productCount} products created`}
            </p>
          </div>
        </div>
        <StatusBadge status={batch.status} />
      </div>

      <div className="w-full bg-bg-tertiary rounded-full h-2 mb-4">
        <div
          className="bg-accent rounded-full h-2 transition-all duration-1000"
          style={{ width: `${Math.max(5, progress)}%` }}
        />
      </div>

      <div className="grid grid-cols-4 gap-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
              step.done ? 'bg-approve/20 text-approve' :
              i === currentStep ? 'bg-accent/20 text-accent' :
              'bg-bg-tertiary text-text-tertiary'
            }`}>
              {step.done ? '✓' : i + 1}
            </span>
            <span className={`text-xs ${step.done ? 'text-text-secondary' : i === currentStep ? 'text-accent' : 'text-text-tertiary'}`}>
              {step.label}
            </span>
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
      <p className="text-xs text-text-tertiary mb-2">{item.archetype.replace(/_/g, ' ')}</p>
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

function DesignDetail({ design, onBack, onApprove, onReject, onDelay }: {
  design: DesignOut;
  onBack: () => void;
  onApprove: () => void;
  onReject: () => void;
  onDelay: () => void;
}) {
  return (
    <div>
      <button onClick={onBack} className="text-text-secondary hover:text-text-primary text-sm mb-4">
        &larr; Back to queue
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          {design.processed_image_url ? (
            <ClickableImage src={design.processed_image_url} alt={design.concept_name} className="w-full rounded-xl" />
          ) : (
            <div className="w-full h-64 bg-bg-tertiary rounded-xl flex items-center justify-center text-text-tertiary">
              Text Only Design
            </div>
          )}
          {design.image_prompt && (
            <div className="mt-4 p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-1">Image Prompt</p>
              <p className="text-sm text-text-secondary">{design.image_prompt}</p>
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
              {design.version > 1 && <span className="text-xs text-text-tertiary">v{design.version}</span>}
            </div>
          </div>

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

          {design.font_pair && (
            <div className="p-3 bg-bg-secondary rounded-lg border border-border">
              <p className="text-xs text-text-tertiary mb-1">Font Pair</p>
              <p className="text-sm text-text-primary">{design.font_pair}</p>
              {design.font_reasoning && <p className="text-xs text-text-secondary mt-1">{design.font_reasoning}</p>}
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

          <div className="flex gap-3 pt-4 border-t border-border">
            <button onClick={onReject} className="flex-1 py-2.5 rounded-lg bg-reject/20 text-reject font-semibold text-sm hover:bg-reject/30 transition-colors">
              Reject
            </button>
            <button onClick={onDelay} className="flex-1 py-2.5 rounded-lg bg-delay/20 text-delay font-semibold text-sm hover:bg-delay/30 transition-colors">
              Delay
            </button>
            <button onClick={onApprove} className="flex-1 py-2.5 rounded-lg bg-approve/20 text-approve font-semibold text-sm hover:bg-approve/30 transition-colors">
              Approve
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReviewPage() {
  const { queue, sessionActions, isLoading, error, fetchQueue, approveDesign, rejectDesign, delayDesign } = useReviewStore();
  const [selectedDesign, setSelectedDesign] = useState<DesignOut | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [runningBatch, setRunningBatch] = useState<BatchOut | null>(null);
  const [recentBatch, setRecentBatch] = useState<BatchOut | null>(null);
  const [productCount, setProductCount] = useState(0);
  const [triggering, setTriggering] = useState(false);

  const checkBatchStatus = useCallback(async () => {
    try {
      const batches = await listBatches();
      const latest = batches[0];
      if (latest?.status === 'running') {
        setRunningBatch(latest);
        setRecentBatch(null);
        const products = await listProducts();
        setProductCount(products.length);
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
    checkBatchStatus();
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!runningBatch) return;
    const interval = setInterval(checkBatchStatus, 5000);
    return () => clearInterval(interval);
  }, [runningBatch, checkBatchStatus]);

  const handleTrigger = async () => {
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

  const pending = queue.filter((d) => !sessionActions[d.id]);
  const actioned = queue.filter((d) => sessionActions[d.id]);

  const openDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const design = await getDesign(id);
      setSelectedDesign(design);
    } catch { /* ignore */ }
    setLoadingDetail(false);
  };

  const handleAction = async (action: 'approve' | 'reject' | 'delay', id: string) => {
    if (action === 'approve') await approveDesign(id);
    else if (action === 'reject') await rejectDesign(id);
    else {
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
        onApprove={() => handleAction('approve', selectedDesign.id)}
        onReject={() => handleAction('reject', selectedDesign.id)}
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

      {runningBatch && <BatchProgress batch={runningBatch} productCount={productCount} />}
      {recentBatch && <BatchComplete batch={recentBatch} onRefresh={handleRefresh} />}

      {pending.length === 0 && actioned.length === 0 && !runningBatch && !recentBatch && (
        <div className="text-center py-20 text-text-tertiary">
          <p className="text-lg">No designs to review</p>
          <p className="text-sm mt-1">Click "Run Batch" to generate new designs</p>
        </div>
      )}

      {pending.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {pending.map((item) => (
            <DesignCard key={item.id} item={item} onClick={() => openDetail(item.id)} />
          ))}
        </div>
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
