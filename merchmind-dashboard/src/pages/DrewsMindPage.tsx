import { useEffect, useState } from 'react';
import { listIdeas, createIdea, type CustomIdea } from '../api/ideas';
import { getDesign } from '../api/designs';
import type { DesignOut } from '../types/api';
import StatusBadge from '../components/shared/StatusBadge';
import ClickableImage from '../components/shared/ClickableImage';
import { formatTimeAgo } from '../utils/formatters';

const ARCHETYPE_OPTIONS = [
  { value: '', label: 'Let AI decide' },
  { value: 'illustration', label: 'Illustration — detailed graphic' },
  { value: 'hybrid', label: 'Hybrid — graphic + text space' },
  { value: 'text_icon', label: 'Text + Icon — bold symbol' },
  { value: 'typographic', label: 'Typographic — letters as art' },
  { value: 'text_only', label: 'Text Only — slogan/phrase' },
];

function IdeaResult({ idea }: { idea: CustomIdea }) {
  const [design, setDesign] = useState<DesignOut | null>(null);

  useEffect(() => {
    if (idea.design_id) {
      getDesign(idea.design_id).then(setDesign).catch(() => null);
    }
  }, [idea.design_id]);

  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-sm font-semibold text-text-primary">{idea.input_text}</p>
          <p className="text-xs text-text-tertiary mt-0.5">{formatTimeAgo(idea.created_at)}</p>
        </div>
        <StatusBadge status={idea.status} />
      </div>

      {design && (
        <div className="flex gap-4 mt-3 pt-3 border-t border-border">
          {design.processed_image_url ? (
            <ClickableImage src={design.processed_image_url} alt={design.concept_name} className="w-24 h-24 object-cover rounded-lg shrink-0" />
          ) : (
            <div className="w-24 h-24 bg-bg-tertiary rounded-lg flex items-center justify-center text-text-tertiary text-xs shrink-0">
              {design.archetype}
            </div>
          )}
          <div className="min-w-0">
            <p className="text-sm text-text-primary font-medium">{design.shopify_title || design.concept_name}</p>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge status={design.archetype} />
              {design.image_api_used && (
                <span className="text-xs text-text-tertiary">via {design.image_api_used}</span>
              )}
            </div>
            {design.shopify_tags && design.shopify_tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {design.shopify_tags.slice(0, 6).map((tag) => (
                  <span key={tag} className="px-1.5 py-0.5 bg-bg-tertiary rounded text-xs text-text-tertiary">{tag}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DrewsMindPage() {
  const [ideas, setIdeas] = useState<CustomIdea[]>([]);
  const [inputText, setInputText] = useState('');
  const [archetype, setArchetype] = useState('');
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listIdeas().then(setIdeas).catch(() => null).finally(() => setLoading(false));
  }, []);

  const handleSubmit = async () => {
    if (!inputText.trim() || generating) return;
    setGenerating(true);
    try {
      const prefs: Record<string, string> = {};
      if (archetype) prefs.archetype = archetype;
      await createIdea(inputText.trim(), prefs);
      setInputText('');
      setArchetype('');
      const updated = await listIdeas();
      setIdeas(updated);
    } catch { /* ignore */ }
    setGenerating(false);
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>;

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">Drew's Mind</h1>
        <p className="text-sm text-text-secondary mt-1">Turn your ideas into merch designs. Type anything — a phrase, concept, feeling — and MerchMind will create it.</p>
      </div>

      <div className="bg-bg-secondary border border-accent/30 rounded-xl p-5 mb-6">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="What's on your mind? A funny phrase, a design concept, a feeling you want to capture..."
          className="w-full bg-bg-tertiary border border-border rounded-lg px-4 py-3 text-sm text-text-primary placeholder-text-tertiary resize-none focus:outline-none focus:border-accent"
          rows={3}
          disabled={generating}
        />

        <div className="flex items-center gap-3 mt-3">
          <select
            value={archetype}
            onChange={(e) => setArchetype(e.target.value)}
            className="bg-bg-tertiary border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
            disabled={generating}
          >
            {ARCHETYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <button
            onClick={handleSubmit}
            disabled={!inputText.trim() || generating}
            className="ml-auto px-5 py-2 rounded-lg bg-accent text-white font-semibold text-sm hover:bg-accent/80 transition-colors disabled:opacity-50"
          >
            {generating ? 'Creating...' : 'Generate Design'}
          </button>
        </div>

        {generating && (
          <div className="flex items-center gap-2 mt-3">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <p className="text-xs text-accent">Generating your design — classifying, creating image, building products...</p>
          </div>
        )}
      </div>

      {ideas.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-3">Your Ideas</h2>
          <div className="space-y-3">
            {ideas.map((idea) => (
              <IdeaResult key={idea.id} idea={idea} />
            ))}
          </div>
        </div>
      )}

      {ideas.length === 0 && !generating && (
        <div className="text-center py-12 text-text-tertiary">
          <p className="text-lg">No ideas yet</p>
          <p className="text-sm mt-1">Type something above and hit Generate</p>
        </div>
      )}
    </div>
  );
}
