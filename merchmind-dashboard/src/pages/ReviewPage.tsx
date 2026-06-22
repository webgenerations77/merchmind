import { useEffect, useState, useCallback } from 'react';
import { useReviewStore } from '../stores/reviewStore';
import { getDesign, getReviewQueue } from '../api/designs';
import { listBatches, triggerBatch } from '../api/batches';
import { listProducts } from '../api/products';
import { getApiBalance, type ApiBalanceResult } from '../api/health';
import MockupTabs from '../components/shared/MockupTabs';
import SuggestDrawer from '../components/shared/SuggestDrawer';
import type { DesignOut, DesignQueueItem, BatchOut, ProductOut } from '../types/api';
import ConfidenceBadge from '../components/shared/ConfidenceBadge';
import StatusBadge from '../components/shared/StatusBadge';
import { formatCurrency, formatProductType, toTitleCase } from '../utils/formatters';
import { calculateCostBreakdown } from '../utils/profitCalc';

function BatchProgress({ batch, productCount, designCount }: { batch: BatchOut; productCount: number; designCount: number }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const start = new Date(batch.run_started_at).getTime();
    setElapsed(Math.floor((Date.now() - start) / 1000));
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [batch.run_started_at]);

  const totalDesigns = batch.queued_count || 0;
  const designsDone = designCount;
  const progressPct = totalDesigns > 0
    ? Math.min(95, ((designsDone / totalDesigns) * 80) + (batch.total_ideas > 0 ? 10 : 0) + (batch.queued_count > 0 ? 10 : 0))
    : batch.total_ideas > 0 ? 15 : 5;

  const scraped = batch.total_ideas > 0;
  const scored = scraped && batch.queued_count > 0;
  const generated = scored && totalDesigns > 0 && designsDone >= totalDesigns;
  const productsCreated = generated && productCount > 0;
  const steps = [
    { label: 'Scraping trends', detail: scraped ? `${batch.total_ideas} found` : '', done: scraped },
    { label: 'Scoring & filtering', detail: scored ? `${batch.queued_count} qualified` : '', done: scored },
    { label: 'Generating designs', detail: scored ? `${designsDone}/${totalDesigns}` : '', done: generated },
    { label: 'Creating products', detail: productsCreated ? `${productCount} created` : '', done: productsCreated },
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

const ARCHETYPE_LABELS: Record<string, string> = {
  illustration: 'Illustration',
  hybrid: 'Hybrid',
  text_icon: 'Text + Icon',
  typographic: 'Typography',
  text_only: 'Text',
};

const SOURCE_LABELS: Record<string, string> = {
  google: 'Google Trends',
  reddit: 'Reddit',
  twitter: 'Twitter/X',
  seasonal: 'Seasonal Calendar',
  manual: 'Manual Entry',
};

function AiReasoningSection({ design, products }: { design: DesignOut; products: ProductOut[] }) {
  const [open, setOpen] = useState(false);

  const hasTrend = !!(design.trend_source || design.claude_reasoning);
  const hasQualityBreakdown = !!design.quality_breakdown;
  const hasProductReasoning = !!design.primary_product_type_reasoning;
  const hasTextScoring = !!design.text_concept_scoring;
  const hasAnyReasoning = hasTrend || hasQualityBreakdown || hasProductReasoning || hasTextScoring;

  return (
    <div className="bg-bg-secondary rounded-lg border border-border overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3 hover:bg-bg-tertiary/50 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-purple-400 text-sm">&#9670;</span>
          <span className="text-sm font-medium text-text-primary">Why did the AI create this?</span>
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`w-4 h-4 text-text-tertiary transition-transform ${open ? 'rotate-180' : ''}`}
        >
          <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
        </svg>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-4">
          {!hasAnyReasoning ? (
            <p className="text-sm text-text-tertiary italic">Reasoning not available for this concept.</p>
          ) : (
            <>
              {hasTrend && (
                <div>
                  <p className="text-xs font-semibold text-purple-400 uppercase tracking-wide mb-1.5">Trend Source</p>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {design.trend_source && (
                      <>Spotted on <span className="text-text-primary font-medium">{SOURCE_LABELS[design.trend_source] || design.trend_source}</span></>
                    )}
                    {design.trend_source_metadata?.subreddit != null && (
                      <> in <span className="text-text-primary font-medium">r/{String(design.trend_source_metadata.subreddit)}</span></>
                    )}
                    {design.trend_signal && (
                      <> &mdash; &ldquo;{design.trend_signal}&rdquo;</>
                    )}
                    {design.trend_source_metadata?.volume_change != null && (
                      <>, search volume {String(design.trend_source_metadata.volume_change)}</>
                    )}
                    {'.'}
                  </p>
                  {(design.trend_score != null || design.viability_score != null) && (
                    <p className="text-xs text-text-tertiary mt-1">
                      Trend strength {design.trend_score ?? '?'}/100, merch viability {design.viability_score ?? '?'}/100
                      {design.final_score != null && <> (combined {design.final_score}/100)</>}
                      {'.'}
                    </p>
                  )}
                  {design.claude_reasoning && (
                    <p className="text-sm text-text-secondary mt-1.5 leading-relaxed">{design.claude_reasoning}</p>
                  )}
                </div>
              )}

              {hasQualityBreakdown && (
                <div>
                  <p className="text-xs font-semibold text-purple-400 uppercase tracking-wide mb-1.5">Quality Assessment</p>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {'This '}
                    {ARCHETYPE_LABELS[design.archetype]?.toLowerCase() || design.archetype.replace(/_/g, ' ')}
                    {' design scored '}
                    <span className="text-text-primary font-medium">{design.quality_score}/40</span>
                    {' overall. '}
                    {Object.entries(design.quality_breakdown!).map(([key, val], i, arr) => {
                      const label = key.replace(/_/g, ' ');
                      const strength = val >= 8 ? 'strong' : val >= 6 ? 'solid' : 'weaker';
                      return (
                        <span key={key}>
                          {i === arr.length - 1 && arr.length > 1 ? 'and ' : ''}
                          <span className="capitalize">{label}</span>
                          {' was '}
                          <span className={val >= 8 ? 'text-approve' : val >= 6 ? 'text-text-primary' : 'text-confidence-medium'}>
                            {strength} ({val}/10)
                          </span>
                          {i < arr.length - 1 ? ', ' : '.'}
                        </span>
                      );
                    })}
                  </p>
                </div>
              )}

              {products.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-purple-400 uppercase tracking-wide mb-1.5">Product Selection</p>
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {'Assigned to '}
                    <span className="text-text-primary font-medium">{products.length} product type{products.length !== 1 ? 's' : ''}</span>
                    {': '}
                    {products.map((p) => formatProductType(p.product_type)).join(', ')}
                    {'. '}
                    {design.primary_product_type && (
                      <>
                        <span className="text-text-primary font-medium">{formatProductType(design.primary_product_type)}</span>
                        {' was chosen as the primary product type.'}
                      </>
                    )}
                  </p>
                  {hasProductReasoning && (
                    <p className="text-sm text-text-secondary mt-1.5 leading-relaxed">{design.primary_product_type_reasoning}</p>
                  )}
                </div>
              )}

              {hasTextScoring && (
                <div>
                  <p className="text-xs font-semibold text-purple-400 uppercase tracking-wide mb-1.5">Text Selection</p>
                  <p className="text-sm text-text-secondary leading-relaxed mb-2">
                    {'The AI evaluated '}
                    <span className="text-text-primary font-medium">{design.text_concept_scoring!.candidates.length} text candidates</span>
                    {' and selected the highest-scoring option:'}
                  </p>
                  <div className="space-y-2">
                    {design.text_concept_scoring!.candidates.map((c, i) => {
                      const isSelected = i === design.text_concept_scoring!.selected_index;
                      return (
                        <div key={i} className={`p-2 rounded-lg border ${
                          isSelected ? 'border-accent/50 bg-accent/5' : 'border-border/50 bg-bg-tertiary/50'
                        }`}>
                          <div className="flex items-center justify-between mb-1">
                            <span className={`text-sm font-semibold ${isSelected ? 'text-accent' : 'text-text-secondary'}`}>
                              &ldquo;{c.text}&rdquo;
                              {isSelected && (
                                <span className="ml-2 text-[10px] font-bold uppercase bg-accent/20 text-accent px-1.5 py-0.5 rounded">Selected</span>
                              )}
                            </span>
                            <span className="text-xs font-bold text-text-primary">{c.total}/40</span>
                          </div>
                          <div className="flex gap-3 mb-1">
                            {Object.entries(c.scores).map(([key, val]) => (
                              <span key={key} className="text-[10px] text-text-tertiary">
                                {key}: <span className="text-text-secondary font-medium">{val}</span>
                              </span>
                            ))}
                          </div>
                          <p className="text-xs text-text-secondary italic">{c.rationale}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function DesignCard({ item, action, onClick, onToggleFeatured }: {
  item: DesignQueueItem;
  action?: string;
  onClick: () => void;
  onToggleFeatured?: (id: string) => void;
}) {
  const handleStar = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleFeatured?.(item.id);
  };

  return (
    <button
      onClick={onClick}
      className="group bg-bg-secondary border border-border rounded-xl overflow-hidden text-left hover:border-accent/50 transition-all w-full flex flex-col"
    >
      {/* PRIMARY: Large mockup image */}
      <div className="relative w-full aspect-square bg-bg-tertiary">
        {(item.primary_mockup_url || item.processed_image_url) ? (
          <img
            src={item.primary_mockup_url || item.processed_image_url!}
            alt={item.concept_name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-text-tertiary text-sm">
            Text Only
          </div>
        )}

        {/* Featured star overlay */}
        <div
          onClick={handleStar}
          className={`absolute top-2 right-2 w-8 h-8 rounded-full flex items-center justify-center transition-all cursor-pointer ${
            item.is_featured
              ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/30'
              : 'bg-black/40 text-white/60 opacity-0 group-hover:opacity-100 hover:bg-black/60 hover:text-amber-400'
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clipRule="evenodd" />
          </svg>
        </div>

        {/* Session action overlay */}
        {action && (
          <div className="absolute bottom-2 left-2">
            <StatusBadge status={action} />
          </div>
        )}

        {/* Revisit badge overlay */}
        {(item.revisit_count ?? 0) > 0 && (
          <div className="absolute top-2 left-2">
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase bg-blue-500/80 text-white backdrop-blur-sm">
              Revisit{item.revisit_count! > 1 ? ` x${item.revisit_count}` : ''}
            </span>
          </div>
        )}
      </div>

      {/* Card info */}
      <div className="p-3 flex flex-col gap-2">
        {/* SECONDARY: Title + classification + featured */}
        <div>
          <h3 className="text-sm font-semibold text-text-primary leading-tight line-clamp-2">
            {toTitleCase(item.concept_name)}
          </h3>
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
              item.classification === 'collection'
                ? 'bg-purple-500/20 text-purple-400'
                : 'bg-accent/20 text-accent'
            }`}>
              {item.classification === 'collection' ? 'Collection' : 'Idea'}
            </span>
          </div>
        </div>

        {/* TERTIARY: Quality score, product count, style tag */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <ConfidenceBadge score={item.quality_score} />
          {(item.product_count ?? 0) > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-bg-tertiary text-text-tertiary">
              {item.product_count} product{item.product_count !== 1 ? 's' : ''}
            </span>
          )}
          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-bg-tertiary text-text-tertiary">
            {ARCHETYPE_LABELS[item.archetype] || item.archetype.replace(/_/g, ' ')}
          </span>
        </div>
      </div>
    </button>
  );
}

function DesignDetail({ design, onBack, onApprove, onReject, onArchive, onRevisit, onSuggestRegenerated, onToggleFeatured }: {
  design: DesignOut;
  onBack: () => void;
  onApprove: (productTypes?: string[]) => void;
  onReject: () => void;
  onArchive: () => void;
  onRevisit: () => void;
  onSuggestRegenerated: () => void;
  onToggleFeatured?: () => void;
}) {
  const [products, setProducts] = useState<ProductOut[]>([]);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [selectedPublishTypes, setSelectedPublishTypes] = useState<Set<string>>(new Set());
  const [isFeatured, setIsFeatured] = useState(design.is_featured);
  const [showSuggestDrawer, setShowSuggestDrawer] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);

  useEffect(() => {
    listProducts().then((all) => {
      const matched = all.filter((p) => p.design_id === design.id);
      setProducts(matched);
      setSelectedPublishTypes(new Set(matched.map((p) => p.product_type)));
    }).catch(() => null);
  }, [design.id]);

  return (
    <div>
      <button onClick={onBack} className="text-text-secondary hover:text-text-primary text-sm mb-4">
        &larr; Back to queue
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MockupTabs
          products={products}
          designImageUrl={design.processed_image_url}
          designName={design.concept_name}
          defaultProductType={design.primary_product_type}
          imageApiUsed={design.image_api_used}
          primaryProductTypeReasoning={design.primary_product_type_reasoning}
        />

        <div className="space-y-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-text-primary">{toTitleCase(design.concept_name)}</h2>
              <button
                onClick={() => { setIsFeatured(!isFeatured); onToggleFeatured?.(); }}
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shrink-0 ${
                  isFeatured
                    ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/30'
                    : 'bg-bg-tertiary text-text-tertiary hover:text-amber-400 hover:bg-amber-500/20'
                }`}
                title={isFeatured ? 'Remove from Featured' : 'Mark as Featured'}
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                  <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
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

          <AiReasoningSection design={design} products={products} />

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
            <button onClick={() => setShowSuggestDrawer(true)} className="py-2.5 px-3 rounded-lg bg-purple-500/20 text-purple-400 font-semibold text-sm hover:bg-purple-500/30 transition-colors">
              Suggest
            </button>
            <button
              onClick={() => setShowPublishDialog(true)}
              disabled={isPublishing}
              className="flex-1 py-2.5 rounded-lg bg-approve/20 text-approve font-semibold text-sm hover:bg-approve/30 disabled:opacity-50 transition-colors"
            >
              {isPublishing ? 'Publishing...' : 'Approve & Publish'}
            </button>
          </div>

          {showSuggestDrawer && (
            <SuggestDrawer
              design={design}
              onClose={() => setShowSuggestDrawer(false)}
              onRegenerated={() => { setShowSuggestDrawer(false); onSuggestRegenerated(); }}
            />
          )}

          {showPublishDialog && (() => {
            const deselectedTypes = products.filter((p) => !selectedPublishTypes.has(p.product_type));
            const noneSelected = selectedPublishTypes.size === 0;
            return (
              <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowPublishDialog(false)}>
                <div className="bg-bg-secondary rounded-2xl border border-border w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
                  <h3 className="text-lg font-bold text-text-primary mb-1">Confirm Publish</h3>
                  <p className="text-xs text-text-secondary mb-4">Select which product types to publish to Shopify.</p>

                  <div className="space-y-2 mb-4">
                    {products.map((p) => {
                      const b = calculateCostBreakdown(p.retail_price, p.printify_base_cost);
                      return (
                        <label key={p.id} className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-bg-tertiary transition-colors">
                          <input
                            type="checkbox"
                            checked={selectedPublishTypes.has(p.product_type)}
                            onChange={(e) => {
                              const next = new Set(selectedPublishTypes);
                              if (e.target.checked) next.add(p.product_type);
                              else next.delete(p.product_type);
                              setSelectedPublishTypes(next);
                            }}
                            className="w-4 h-4 rounded accent-accent shrink-0"
                          />
                          <span className="text-sm text-text-primary flex-1">{formatProductType(p.product_type)}</span>
                          <span className="text-xs text-text-tertiary">{formatCurrency(p.retail_price)}</span>
                          <span className={`text-xs font-medium ${b.netMargin >= 30 ? 'text-approve' : 'text-confidence-medium'}`}>{b.netMargin.toFixed(0)}%</span>
                        </label>
                      );
                    })}
                  </div>

                  {deselectedTypes.length > 0 && !noneSelected && (
                    <p className="text-xs text-amber-400 mb-3">
                      {deselectedTypes.map((p) => formatProductType(p.product_type)).join(', ')} will be permanently removed.
                    </p>
                  )}

                  {noneSelected && (
                    <p className="text-xs text-confidence-low mb-3">
                      At least one product type must be selected.
                    </p>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowPublishDialog(false)}
                      className="flex-1 py-2.5 rounded-lg bg-bg-tertiary border border-border text-sm text-text-secondary hover:text-text-primary transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => { setIsPublishing(true); setShowPublishDialog(false); onApprove(Array.from(selectedPublishTypes)); }}
                      disabled={noneSelected || isPublishing}
                      className="flex-1 py-2.5 rounded-lg bg-approve text-white font-semibold text-sm hover:bg-approve/90 disabled:opacity-50 transition-colors"
                    >
                      {isPublishing ? 'Publishing...' : `Publish ${selectedPublishTypes.size} Product${selectedPublishTypes.size !== 1 ? 's' : ''}`}
                    </button>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

export default function ReviewPage() {
  const { queue, archivedQueue, sessionActions, publishErrors, isLoading, error, fetchQueue, fetchArchived, approveDesign, rejectDesign, archiveDesign, unarchiveDesign, revisitDesign, toggleFeatured } = useReviewStore();
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
        const latestQueue = await getReviewQueue();
        const batchDesigns = latestQueue.filter((d) => d.batch_id === latest.id);
        setBatchDesignCount(batchDesigns.length);
        const batchDesignIds = new Set(batchDesigns.map((d) => d.id));
        const products = await listProducts();
        setProductCount(products.filter((p) => batchDesignIds.has(p.design_id)).length);
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

  const handleAction = async (action: 'approve' | 'reject' | 'archive' | 'revisit', id: string, productTypes?: string[]) => {
    if (action === 'approve') {
      await approveDesign(id, productTypes);
    } else if (action === 'reject') {
      await rejectDesign(id);
    } else if (action === 'archive') {
      await archiveDesign(id);
      fetchArchived();
    } else if (action === 'revisit') {
      await revisitDesign(id);
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
        onSuggestRegenerated={async () => {
          const refreshed = await getDesign(selectedDesign.id).catch(() => null);
          if (refreshed) setSelectedDesign(refreshed);
          else setSelectedDesign(null);
          fetchQueue();
        }}
        onToggleFeatured={() => toggleFeatured(selectedDesign.id)}
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
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
            {batchDesigns.map((item) => (
              <DesignCard key={item.id} item={item} onClick={() => openDetail(item.id)} onToggleFeatured={toggleFeatured} />
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
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {group.designs.map((item) => (
                  <DesignCard key={item.id} item={item} onClick={() => openDetail(item.id)} onToggleFeatured={toggleFeatured} />
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
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
            {drewsDesigns.map((item) => (
              <DesignCard key={item.id} item={item} onClick={() => openDetail(item.id)} onToggleFeatured={toggleFeatured} />
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
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
            {archivedQueue.map((item) => (
              <div key={item.id} className="relative">
                <DesignCard item={item} onClick={() => openDetail(item.id)} onToggleFeatured={toggleFeatured} />
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
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {actioned.map((item) => {
              const pubErr = publishErrors[item.id];
              return (
                <div key={item.id}>
                  <DesignCard
                    item={item}
                    action={sessionActions[item.id]}
                    onClick={() => openDetail(item.id)}
                    onToggleFeatured={toggleFeatured}
                  />
                  {pubErr && pubErr.failed.length > 0 && (
                    <div className="mt-1 p-2 rounded-lg bg-confidence-low/10 border border-confidence-low/30">
                      <p className="text-xs font-semibold text-confidence-low">
                        {pubErr.published.length > 0 ? 'Partial publish' : 'Publish failed'}
                      </p>
                      {pubErr.failed.map((f) => (
                        <p key={f.type} className="text-xs text-text-secondary mt-0.5">
                          {formatProductType(f.type)}: {f.error.slice(0, 80)}
                        </p>
                      ))}
                      {pubErr.published.length === 0 && (
                        <button
                          onClick={() => openDetail(item.id)}
                          className="mt-1 text-xs text-accent hover:underline"
                        >
                          Retry from detail view
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
