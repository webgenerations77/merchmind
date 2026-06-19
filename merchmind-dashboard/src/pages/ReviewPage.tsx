import { useEffect, useState } from 'react';
import { useReviewStore } from '../stores/reviewStore';
import { getDesign } from '../api/designs';
import type { DesignOut, DesignQueueItem } from '../types/api';
import ConfidenceBadge from '../components/shared/ConfidenceBadge';
import StatusBadge from '../components/shared/StatusBadge';

function DesignCard({ item, action, onClick }: { item: DesignQueueItem; action?: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="bg-bg-secondary border border-border rounded-xl p-4 text-left hover:border-accent/50 transition-colors w-full"
    >
      {item.processed_image_url ? (
        <img src={item.processed_image_url} alt={item.concept_name} className="w-full h-40 object-cover rounded-lg mb-3" />
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
            <img src={design.processed_image_url} alt={design.concept_name} className="w-full rounded-xl" />
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

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

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
          <p className="text-sm text-text-secondary mt-1">{pending.length} designs pending review</p>
        </div>
        <button onClick={fetchQueue} className="px-3 py-1.5 rounded-lg bg-bg-secondary border border-border text-sm text-text-secondary hover:text-text-primary transition-colors">
          Refresh
        </button>
      </div>

      {pending.length === 0 && actioned.length === 0 && (
        <div className="text-center py-20 text-text-tertiary">
          <p className="text-lg">No designs to review</p>
          <p className="text-sm mt-1">Trigger a new batch to generate designs</p>
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
