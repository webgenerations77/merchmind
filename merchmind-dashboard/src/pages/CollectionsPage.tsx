import { useEffect, useState } from 'react';
import { listCollections, createCollection, deleteCollection, generateCollectionDesigns, getCollection } from '../api/collections';
import type { CollectionOut } from '../types/api';
import { toTitleCase } from '../utils/formatters';

const ARCHETYPE_OPTIONS = ['', 'illustration', 'hybrid', 'text_icon', 'image_with_text', 'typographic', 'text_only'];

export default function CollectionsPage() {
  const [collections, setCollections] = useState<CollectionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [expandedData, setExpandedData] = useState<CollectionOut | null>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [mood, setMood] = useState('');
  const [palette, setPalette] = useState('');
  const [constraints, setConstraints] = useState('');
  const [archetypeOverride, setArchetypeOverride] = useState('');
  const [maxDesigns, setMaxDesigns] = useState(6);
  const [creating, setCreating] = useState(false);

  const load = () => {
    listCollections().then(setCollections).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    const style_guide: Record<string, unknown> = {};
    if (mood.trim()) style_guide.mood = mood.trim();
    if (palette.trim()) style_guide.palette = palette.split(',').map((c) => c.trim()).filter(Boolean);
    if (constraints.trim()) style_guide.constraints = constraints.trim();
    if (archetypeOverride) style_guide.archetype_override = archetypeOverride;
    await createCollection({ name: name.trim(), description: description.trim() || undefined, style_guide, max_designs: maxDesigns });
    setName(''); setDescription(''); setMood(''); setPalette(''); setConstraints(''); setArchetypeOverride(''); setMaxDesigns(6);
    setShowCreate(false);
    load();
    setCreating(false);
  };

  const handleGenerate = async (id: string) => {
    await generateCollectionDesigns(id);
    load();
  };

  const handleDelete = async (id: string) => {
    await deleteCollection(id);
    if (expanded === id) { setExpanded(null); setExpandedData(null); }
    load();
  };

  const toggleExpand = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      setExpandedData(null);
    } else {
      setExpanded(id);
      const data = await getCollection(id);
      setExpandedData(data);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64 text-text-secondary">Loading...</div>;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">Collections</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors"
        >
          {showCreate ? 'Cancel' : 'New Collection'}
        </button>
      </div>

      {showCreate && (
        <section className="bg-bg-secondary border border-border rounded-xl p-5 space-y-4">
          <h2 className="text-base font-semibold text-text-primary">Create Collection</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-xs text-text-tertiary">Name</label>
              <input
                value={name} onChange={(e) => setName(e.target.value)} placeholder="Summer Vibes 2026"
                className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
              />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-text-tertiary">Description</label>
              <textarea
                value={description} onChange={(e) => setDescription(e.target.value)} rows={2}
                placeholder="A collection of summer-themed designs with bright colors..."
                className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary resize-none"
              />
            </div>
            <div>
              <label className="text-xs text-text-tertiary">Mood / Aesthetic</label>
              <input
                value={mood} onChange={(e) => setMood(e.target.value)} placeholder="playful, retro, nostalgic"
                className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
              />
            </div>
            <div>
              <label className="text-xs text-text-tertiary">Color Palette (comma-separated)</label>
              <input
                value={palette} onChange={(e) => setPalette(e.target.value)} placeholder="#FF6B6B, #4ECDC4, #45B7D1"
                className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
              />
            </div>
            <div>
              <label className="text-xs text-text-tertiary">Archetype Override</label>
              <select
                value={archetypeOverride} onChange={(e) => setArchetypeOverride(e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
              >
                {ARCHETYPE_OPTIONS.map((a) => (
                  <option key={a} value={a}>{a || 'Auto (AI decides)'}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-text-tertiary">Max Designs</label>
              <input
                type="number" min={1} max={12} value={maxDesigns} onChange={(e) => setMaxDesigns(+e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
              />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-text-tertiary">Additional Constraints</label>
              <input
                value={constraints} onChange={(e) => setConstraints(e.target.value)}
                placeholder="No text on designs, minimalist style only..."
                className="mt-1 w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary"
              />
            </div>
          </div>
          <button
            onClick={handleCreate} disabled={!name.trim() || creating}
            className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
          >
            {creating ? 'Creating...' : 'Create Collection'}
          </button>
        </section>
      )}

      {collections.length === 0 ? (
        <div className="bg-bg-secondary border border-border rounded-xl p-12 text-center">
          <p className="text-text-tertiary">No collections yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {collections.map((c) => (
            <div key={c.id} className="bg-bg-secondary border border-border rounded-xl overflow-hidden">
              <div className="p-5">
                <div className="flex items-start justify-between">
                  <button onClick={() => toggleExpand(c.id)} className="text-left flex-1">
                    <h3 className="text-base font-semibold text-text-primary">{c.name}</h3>
                    {c.description && <p className="text-sm text-text-tertiary mt-1">{c.description}</p>}
                    <div className="flex items-center gap-4 mt-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        c.status === 'ready' ? 'bg-approve/15 text-approve' :
                        c.status === 'generating' ? 'bg-accent/15 text-accent' :
                        c.status === 'published' ? 'bg-regen/15 text-regen' :
                        'bg-bg-tertiary text-text-tertiary'
                      }`}>
                        {c.status}
                      </span>
                      <span className="text-xs text-text-tertiary">{c.design_count}/{c.max_designs} designs</span>
                      {c.style_guide.mood && <span className="text-xs text-text-tertiary">Mood: {c.style_guide.mood}</span>}
                    </div>
                  </button>
                  <div className="flex items-center gap-2 ml-4">
                    {c.status !== 'generating' && c.design_count < c.max_designs && (
                      <button
                        onClick={() => handleGenerate(c.id)}
                        className="px-3 py-1.5 bg-accent/15 text-accent rounded-lg text-xs font-medium hover:bg-accent/25 transition-colors"
                      >
                        Generate
                      </button>
                    )}
                    {c.status === 'generating' && (
                      <span className="px-3 py-1.5 text-accent text-xs font-medium animate-pulse">Generating...</span>
                    )}
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="px-3 py-1.5 bg-confidence-low/15 text-confidence-low rounded-lg text-xs font-medium hover:bg-confidence-low/25 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>

              {expanded === c.id && expandedData?.designs && expandedData.designs.length > 0 && (
                <div className="border-t border-border p-5">
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {expandedData.designs.map((d) => (
                      <div key={d.id} className="bg-bg-tertiary rounded-lg overflow-hidden">
                        {d.processed_image_url ? (
                          <img src={d.processed_image_url} alt={d.concept_name} className="w-full aspect-square object-cover" />
                        ) : (
                          <div className="w-full aspect-square bg-bg-primary flex items-center justify-center text-text-tertiary text-xs">
                            No image
                          </div>
                        )}
                        <div className="p-2">
                          <p className="text-xs text-text-primary truncate">{toTitleCase(d.concept_name)}</p>
                          <p className="text-xs text-text-tertiary">{d.archetype} · Q{d.quality_score}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
