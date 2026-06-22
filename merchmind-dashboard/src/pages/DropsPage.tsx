import { useEffect, useState } from 'react';
import { listDrops, getDrop, createDrop, updateDrop, deleteDrop, publishDropNow, removeProductFromDrop } from '../api/drops';
import type { MerchDropOut, MerchDropDetail } from '../types/api';
import StatusBadge from '../components/shared/StatusBadge';
import { formatProductType, formatCurrency } from '../utils/formatters';

function DropStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    scheduled: 'bg-blue-500/20 text-blue-400',
    in_progress: 'bg-amber-500/20 text-amber-400',
    published: 'bg-approve/20 text-approve',
    failed: 'bg-reject/20 text-reject',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${colors[status] || 'bg-bg-tertiary text-text-tertiary'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}

function Countdown({ scheduledAt }: { scheduledAt: string }) {
  const [text, setText] = useState('');
  useEffect(() => {
    const update = () => {
      const diff = new Date(scheduledAt).getTime() - Date.now();
      if (diff <= 0) { setText('Now'); return; }
      const days = Math.floor(diff / 86400000);
      const hours = Math.floor((diff % 86400000) / 3600000);
      const mins = Math.floor((diff % 3600000) / 60000);
      if (days > 0) setText(`${days}d ${hours}h`);
      else if (hours > 0) setText(`${hours}h ${mins}m`);
      else setText(`${mins}m`);
    };
    update();
    const timer = setInterval(update, 60000);
    return () => clearInterval(timer);
  }, [scheduledAt]);
  return <span className="text-xs text-accent font-medium">{text}</span>;
}

function CreateDropForm({ onCreated, onCancel }: { onCreated: () => void; onCancel: () => void }) {
  const [name, setName] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('12:00');
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim() || !date) return;
    setCreating(true);
    try {
      const scheduled_at = new Date(`${date}T${time}:00`).toISOString();
      await createDrop({ name: name.trim(), scheduled_at });
      onCreated();
    } catch { /* ignore */ }
    setCreating(false);
  };

  return (
    <section className="bg-bg-secondary border border-border rounded-xl p-5 space-y-4">
      <h3 className="text-sm font-semibold text-text-primary">New Drop</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label className="text-xs text-text-tertiary block mb-1">Drop Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder='e.g. "Summer Drop Vol. 1"'
            className="w-full px-3 py-2 rounded-lg bg-bg-tertiary border border-border text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent"
          />
        </div>
        <div>
          <label className="text-xs text-text-tertiary block mb-1">Date</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-bg-tertiary border border-border text-sm text-text-primary focus:outline-none focus:border-accent"
          />
        </div>
        <div>
          <label className="text-xs text-text-tertiary block mb-1">Time</label>
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-bg-tertiary border border-border text-sm text-text-primary focus:outline-none focus:border-accent"
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button onClick={onCancel} className="px-3 py-2 rounded-lg bg-bg-tertiary border border-border text-sm text-text-secondary hover:text-text-primary transition-colors">
          Cancel
        </button>
        <button
          onClick={handleCreate}
          disabled={!name.trim() || !date || creating}
          className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/80 disabled:opacity-50 transition-colors"
        >
          {creating ? 'Creating...' : 'Create Drop'}
        </button>
      </div>
    </section>
  );
}

function DropDetail({ drop: initial, onBack, onUpdated }: { drop: MerchDropOut; onBack: () => void; onUpdated: () => void }) {
  const [detail, setDetail] = useState<MerchDropDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(initial.name);
  const [editDate, setEditDate] = useState('');
  const [editTime, setEditTime] = useState('');
  const [publishing, setPublishing] = useState(false);

  const load = () => {
    setLoading(true);
    getDrop(initial.id).then((d) => {
      setDetail(d);
      const dt = new Date(d.scheduled_at);
      setEditDate(dt.toISOString().slice(0, 10));
      setEditTime(dt.toISOString().slice(11, 16));
    }).finally(() => setLoading(false));
  };

  useEffect(load, [initial.id]);

  const handleSave = async () => {
    if (!detail) return;
    const scheduled_at = new Date(`${editDate}T${editTime}:00`).toISOString();
    await updateDrop(detail.id, { name: editName.trim(), scheduled_at });
    setEditing(false);
    load();
    onUpdated();
  };

  const handlePublishNow = async () => {
    if (!detail) return;
    if (!confirm(`Publish "${detail.name}" now? All products will go live immediately.`)) return;
    setPublishing(true);
    try {
      await publishDropNow(detail.id);
      setTimeout(load, 2000);
      onUpdated();
    } catch { /* ignore */ }
    setPublishing(false);
  };

  const handleRemoveProduct = async (productId: string) => {
    if (!detail) return;
    if (!confirm('Remove this product from the drop?')) return;
    await removeProductFromDrop(detail.id, productId);
    load();
    onUpdated();
  };

  const handleDelete = async () => {
    if (!detail) return;
    if (!confirm(`Delete "${detail.name}"? Products will be unassigned but not deleted.`)) return;
    await deleteDrop(detail.id);
    onBack();
    onUpdated();
  };

  if (loading || !detail) {
    return <div className="flex items-center justify-center h-64 text-text-secondary">Loading drop...</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <button onClick={onBack} className="text-text-secondary hover:text-text-primary text-sm">
        &larr; Back to drops
      </button>

      <div className="flex items-start justify-between">
        <div>
          {editing ? (
            <div className="space-y-3">
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="text-xl font-bold bg-bg-tertiary border border-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:border-accent"
              />
              <div className="flex gap-2">
                <input
                  type="date"
                  value={editDate}
                  onChange={(e) => setEditDate(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-bg-tertiary border border-border text-sm text-text-primary focus:outline-none focus:border-accent"
                />
                <input
                  type="time"
                  value={editTime}
                  onChange={(e) => setEditTime(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-bg-tertiary border border-border text-sm text-text-primary focus:outline-none focus:border-accent"
                />
              </div>
              <div className="flex gap-2">
                <button onClick={() => setEditing(false)} className="px-3 py-1.5 rounded-lg bg-bg-tertiary text-sm text-text-secondary">Cancel</button>
                <button onClick={handleSave} className="px-3 py-1.5 rounded-lg bg-accent text-white text-sm font-medium">Save</button>
              </div>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-text-primary">{detail.name}</h1>
              <div className="flex items-center gap-3 mt-2">
                <DropStatusBadge status={detail.status} />
                <span className="text-sm text-text-secondary">
                  {new Date(detail.scheduled_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                </span>
                {detail.status === 'scheduled' && <Countdown scheduledAt={detail.scheduled_at} />}
              </div>
            </>
          )}
        </div>
        <div className="flex gap-2">
          {detail.status === 'scheduled' && !editing && (
            <>
              <button onClick={() => setEditing(true)} className="px-3 py-1.5 rounded-lg bg-bg-secondary border border-border text-sm text-text-secondary hover:text-text-primary transition-colors">
                Edit
              </button>
              <button
                onClick={handlePublishNow}
                disabled={publishing || detail.products.length === 0}
                className="px-4 py-1.5 rounded-lg bg-approve text-white text-sm font-medium hover:bg-approve/90 disabled:opacity-50 transition-colors"
              >
                {publishing ? 'Publishing...' : 'Publish Now'}
              </button>
            </>
          )}
          {(detail.status === 'scheduled' || detail.status === 'failed') && (
            <button onClick={handleDelete} className="px-3 py-1.5 rounded-lg bg-reject/20 text-reject text-sm font-medium hover:bg-reject/30 transition-colors">
              Delete
            </button>
          )}
        </div>
      </div>

      <div className="bg-bg-secondary border border-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-text-primary">Products ({detail.products.length})</h2>
        </div>

        {detail.products.length === 0 ? (
          <p className="text-sm text-text-tertiary text-center py-8">
            No products assigned yet. Schedule designs from the Review page.
          </p>
        ) : (
          <div className="space-y-3">
            {detail.products.map((p) => (
              <div key={p.id} className="flex items-center gap-4 p-3 bg-bg-tertiary rounded-lg">
                <div className="w-14 h-14 rounded-lg overflow-hidden bg-bg-primary shrink-0">
                  {p.mockup_urls?.front || p.processed_image_url ? (
                    <img src={p.mockup_urls?.front || p.processed_image_url!} alt={p.concept_name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-text-tertiary text-xs">N/A</div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{p.concept_name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-text-tertiary">{formatProductType(p.product_type)}</span>
                    <StatusBadge status={p.publish_status} />
                  </div>
                </div>
                <span className="text-sm font-medium text-accent">{formatCurrency(p.retail_price)}</span>
                {detail.status === 'scheduled' && (
                  <button
                    onClick={() => handleRemoveProduct(p.id)}
                    className="text-xs text-reject hover:text-reject/80 transition-colors"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function DropsPage() {
  const [drops, setDrops] = useState<MerchDropOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedDrop, setSelectedDrop] = useState<MerchDropOut | null>(null);

  const load = () => {
    setLoading(true);
    listDrops().then(setDrops).finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (selectedDrop) {
    return <DropDetail drop={selectedDrop} onBack={() => { setSelectedDrop(null); load(); }} onUpdated={load} />;
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Merch Drops</h1>
          <p className="text-sm text-text-secondary mt-1">Schedule coordinated product launches</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/80 transition-colors"
        >
          {showCreate ? 'Cancel' : 'New Drop'}
        </button>
      </div>

      {showCreate && <CreateDropForm onCreated={() => { setShowCreate(false); load(); }} onCancel={() => setShowCreate(false)} />}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-text-secondary">Loading drops...</div>
      ) : drops.length === 0 ? (
        <div className="text-center py-16 text-text-tertiary">
          <p className="text-lg">No drops yet</p>
          <p className="text-sm mt-1">Create a drop and schedule designs from the Review page</p>
        </div>
      ) : (
        <div className="space-y-3">
          {drops.map((drop) => (
            <button
              key={drop.id}
              onClick={() => setSelectedDrop(drop)}
              className="w-full bg-bg-secondary border border-border rounded-xl p-5 text-left hover:border-accent/50 transition-all"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-text-primary">{drop.name}</h3>
                  <div className="flex items-center gap-3 mt-1.5">
                    <DropStatusBadge status={drop.status} />
                    <span className="text-xs text-text-secondary">
                      {new Date(drop.scheduled_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                    </span>
                    {drop.status === 'scheduled' && <Countdown scheduledAt={drop.scheduled_at} />}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-lg font-bold text-text-primary">{drop.product_count}</span>
                  <p className="text-xs text-text-tertiary">product{drop.product_count !== 1 ? 's' : ''}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
