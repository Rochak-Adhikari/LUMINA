// frontend/pages/MemoryPage.jsx — presentation only. State via useMemory.
import React, { useMemo, useState } from 'react';
import { Brain, Plus, X } from 'lucide-react';
import { PageHeader, GlassCard, StatTile, SearchBox } from '../components/ui';
import { EmptyState, SelectField, TextArea, FieldLabel } from '../components/workspace';
import { useMemory } from '../hooks/useMemory';
import { cn } from '../utils/cn';

const TYPES = [
  { value: 'fact', label: 'Fact' },
  { value: 'preference', label: 'Preference' },
  { value: 'conversation_summary', label: 'Conversation Summary' },
];

export default function MemoryPage() {
  const { memories, stats, loading, add } = useMemory();
  const [query, setQuery] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ type: 'fact', content: '' });
  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleAdd = () => {
    if (!form.content.trim()) return;
    add(form.type, form.content.trim());
    setForm({ type: 'fact', content: '' });
    setShowForm(false);
  };

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    if (!q) return memories;
    return memories.filter((m) => (m.content || '').toLowerCase().includes(q) || (m.type || '').toLowerCase().includes(q));
  }, [memories, query]);

  const total = stats?.total ?? memories.length;

  return (
    <div>
      <PageHeader
        title="Memory" subtitle="Stored facts, preferences, retrieval" icon={Brain}
        actions={
          <button onClick={() => setShowForm((s) => !s)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-primary-container/30 bg-primary-container/10 px-3 py-1.5 text-xs text-primary hover:bg-primary-container/20 transition-all duration-200">
            {showForm ? <X size={14} /> : <Plus size={14} />}
            {showForm ? 'Cancel' : 'Add Memory'}
          </button>
        }
      />

      {/* Stats */}
      <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Total" value={loading ? '…' : total} />
        <StatTile label="Facts" value={stats?.fact ?? '—'} />
        <StatTile label="Preferences" value={stats?.preference ?? '—'} />
        <StatTile label="Summaries" value={stats?.conversation_summary ?? '—'} />
      </div>

      {showForm && (
        <GlassCard className="mb-6 p-5">
          <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-primary/70">New Memory</h3>
          <div className="flex flex-col gap-3">
            <div>
              <FieldLabel>Type</FieldLabel>
              <SelectField value={form.type} onChange={(e) => setField('type', e.target.value)} options={TYPES} />
            </div>
            <TextArea rows={3} value={form.content} onChange={(e) => setField('content', e.target.value)} placeholder="What should Lumina remember?" />
            <button onClick={handleAdd} disabled={!form.content.trim()}
              className={cn('self-end rounded-lg border px-4 py-2 text-xs transition-all duration-200',
                form.content.trim() ? 'border-primary-container/50 bg-primary-container/10 text-primary hover:bg-primary-container/20'
                  : 'border-white/10 text-on-surface-variant/40 cursor-not-allowed')}>
              Save Memory
            </button>
          </div>
        </GlassCard>
      )}

      <div className="mx-auto mb-5 max-w-xl">
        <SearchBox value={query} onChange={setQuery} placeholder="Search memories…" />
      </div>

      {filtered.length > 0 ? (
        <div className="flex flex-col gap-3">
          {filtered.map((m) => (
            <GlassCard key={m.id} className="p-4">
              <div className="mb-1 flex items-center gap-2">
                <span className="rounded-full border border-primary-container/25 bg-primary-container/5 px-2 py-0.5 text-[10px] text-primary/70">{m.type}</span>
                {m.created_at && <span className="text-[10px] text-on-surface-variant/40">{new Date(m.created_at).toLocaleDateString()}</span>}
              </div>
              <p className="text-sm text-on-surface-variant/80 leading-relaxed">{m.content}</p>
            </GlassCard>
          ))}
        </div>
      ) : (
        <EmptyState icon={Brain} title={loading ? 'Loading memories…' : 'No memories stored yet'} hint='Click "Add Memory" to store facts and preferences.' />
      )}
    </div>
  );
}
