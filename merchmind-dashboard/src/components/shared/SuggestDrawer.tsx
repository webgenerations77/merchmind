import { useState, useRef, useEffect } from 'react';
import { X, Loader2 } from 'lucide-react';
import { sendChatMessage, suggestRegenerate, clearChat } from '../../api/designs';
import type { DesignOut } from '../../types/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const VIBE_OPTIONS = ['funny', 'minimal', 'nostalgic', 'dark', 'ironic', 'hopeful', 'bold', 'weird', 'clean'];
const CHANGE_OPTIONS = ['concept', 'typography', 'layout', 'color palette', 'illustration style', 'everything'];
const AUDIENCE_OPTIONS = ['teens', 'parents', 'gift buyers', 'hobbyists', 'niche community', 'gen z', 'millennials'];

function Pill({ label, selected, onClick }: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
        selected
          ? 'bg-[#3aaa6e] text-white border border-transparent'
          : 'bg-[#0d0f0e] text-[#f0ede6] border border-[#f0ede6]/30 hover:border-[#f0ede6]/60'
      }`}
    >
      {label}
    </button>
  );
}

export default function SuggestDrawer({
  design,
  onClose,
  onRegenerated,
}: {
  design: DesignOut;
  onClose: () => void;
  onRegenerated: (version: number) => void;
}) {
  const [messages, setMessages] = useState<Message[]>(design.conversation_history ?? []);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vibe, setVibe] = useState<string[]>([]);
  const [changeFocus, setChangeFocus] = useState<string | null>(null);
  const [audience, setAudience] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput('');
    setError(null);
    setSending(true);

    const optimistic: Message[] = [...messages, { role: 'user', content: text }];
    setMessages(optimistic);

    try {
      const res = await sendChatMessage(design.id, text);
      setMessages(res.conversation);
    } catch (e) {
      setError('Failed to get a response. Try again.');
      setMessages(optimistic);
    }
    setSending(false);
    inputRef.current?.focus();
  };

  const toggleVibe = (v: string) =>
    setVibe((prev) =>
      prev.includes(v) ? prev.filter((x) => x !== v) : prev.length < 3 ? [...prev, v] : prev,
    );

  const toggleAudience = (a: string) =>
    setAudience((prev) => (prev.includes(a) ? prev.filter((x) => x !== a) : [...prev, a]));

  const handleRegenerate = async () => {
    if (regenerating || messages.length === 0) return;
    setRegenerating(true);
    setError(null);
    const brief = {
      vibe: vibe.length ? vibe : undefined,
      change_focus: changeFocus ?? undefined,
      audience: audience.length ? audience : undefined,
    };
    try {
      const res = await suggestRegenerate(design.id, messages, brief);
      onRegenerated(res.version);
    } catch {
      setError('Regeneration failed. Try again.');
      setRegenerating(false);
    }
  };

  const handleClear = async () => {
    await clearChat(design.id).catch(() => null);
    setMessages([]);
    setError(null);
    setVibe([]);
    setChangeFocus(null);
    setAudience([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50" />
      <div
        className="relative w-full max-w-md h-full bg-bg-primary border-l border-border flex flex-col animate-slide-in-right"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border shrink-0">
          <div>
            <h3 className="text-sm font-bold text-text-primary">Suggest Changes</h3>
            <p className="text-xs text-text-tertiary mt-0.5 truncate max-w-[280px]">{design.concept_name}</p>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={handleClear}
                className="text-xs text-text-tertiary hover:text-text-secondary transition-colors"
              >
                Clear
              </button>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-text-tertiary hover:text-text-primary hover:bg-bg-tertiary transition-colors"
            >
              <X size={20} strokeWidth={2} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && !sending && (
            <div className="text-center py-8">
              <p className="text-sm text-text-tertiary">Start a conversation to iterate on this concept.</p>
              <p className="text-xs text-text-tertiary mt-2">Try: &ldquo;Make it more playful&rdquo; or &ldquo;Change the text to...&rdquo;</p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-accent text-white rounded-br-md'
                  : 'bg-bg-secondary border border-border text-text-primary rounded-bl-md'
              }`}>
                {msg.content}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="bg-bg-secondary border border-border rounded-2xl rounded-bl-md px-3.5 py-2.5">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          {error && (
            <p className="text-xs text-center text-confidence-low">{error}</p>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input + Regenerate */}
        <div className="border-t border-border p-3 space-y-2 shrink-0">
          {/* Pre-populated question controls */}
          <div className="space-y-2.5 max-h-48 overflow-y-auto">
            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-text-secondary">What's the core vibe? <span className="font-normal text-text-tertiary">(pick 1–3)</span></p>
              <div className="flex flex-wrap gap-1.5">
                {VIBE_OPTIONS.map((v) => (
                  <Pill key={v} label={v} selected={vibe.includes(v)} onClick={() => toggleVibe(v)} />
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-text-secondary">What should change most?</p>
              <div className="flex flex-wrap gap-1.5">
                {CHANGE_OPTIONS.map((c) => (
                  <Pill
                    key={c}
                    label={c}
                    selected={changeFocus === c}
                    onClick={() => setChangeFocus((prev) => (prev === c ? null : c))}
                  />
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-text-secondary">Who's this for?</p>
              <div className="flex flex-wrap gap-1.5">
                {AUDIENCE_OPTIONS.map((a) => (
                  <Pill key={a} label={a} selected={audience.includes(a)} onClick={() => toggleAudience(a)} />
                ))}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe what you'd change..."
              rows={1}
              className="flex-1 bg-bg-secondary border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-tertiary resize-none focus:outline-none focus:border-accent transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="px-3 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-40 hover:bg-accent/80 transition-colors shrink-0"
            >
              Send
            </button>
          </div>

          {messages.length >= 2 && (
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="w-full py-2.5 rounded-lg bg-accent/20 text-accent font-semibold text-sm hover:bg-accent/30 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {regenerating ? (
                <>
                  <Loader2 size={16} strokeWidth={2} className="animate-spin" />
                  Regenerating...
                </>
              ) : (
                'Regenerate with this conversation'
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
