// frontend/pages/Workspace/ArchiveView.jsx — presentation only, state via useArchive
import React, { useState } from 'react';
import { Archive, Pin, ChevronDown, ChevronUp } from 'lucide-react';
import { GlassCard, SearchBox } from '../../components/ui';
import { useArchive } from '../../hooks/useWorkspace';
import {
  WorkspaceToolbar, ErrorToast, EmptyState, FilterTabs, TextField, TextArea,
} from '../../components/workspace';
import { cn } from '../../utils/cn';

const CATEGORIES = ['All', 'project', 'study', 'health', 'idea', 'bug', 'fix', 'personal'];
const parseTags = (s) => (s ? s.split(',').map((t) => t.trim()).filter(Boolean) : []);

export function ArchiveView() {
  const { items: notes, error, create, update, remove } = useArchive();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All');
  const [expandedId, setExpandedId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', body: '', tags: '' });
  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleAdd = () => {
    if (!form.title.trim() || !form.body.trim()) return;
    create({ title: form.title.trim(), body: form.body.trim(), tags: form.tags.trim() });
    setForm({ title: '', body: '', tags: '' });
    setShowForm(false);
  };
  const togglePin = (note) => update({ id: note.id, pinned: note.pinned ? 0 : 1 });

  const filtered = notes.filter((note) => {
    const q = query.toLowerCase();
    const matchesSearch = !q || note.title.toLowerCase().includes(q) || note.body.toLowerCase().includes(q);
    const matchesCat = category === 'All' || (note.tags && note.tags.toLowerCase().includes(category.toLowerCase()));
    return matchesSearch && matchesCat;
  });
  const tabs = CATEGORIES.map((c) => ({ id: c, label: c === 'All' ? 'All' : c }));

  return (
    <div>
      <WorkspaceToolbar
        title="Knowledge Archive" subtitle="Notes, decisions, ideas" icon={Archive}
        addLabel="Add Note" showForm={showForm} onToggleForm={() => setShowForm((s) => !s)}
      />
      <ErrorToast message={error} />

      {showForm && (
        <GlassCard className="mb-6 p-5">
          <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-primary/70">New Note</h3>
          <div className="flex flex-col gap-3">
            <TextField value={form.title} onChange={(e) => setField('title', e.target.value)} placeholder="Title" />
            <TextArea rows={4} value={form.body} onChange={(e) => setField('body', e.target.value)} placeholder="Note body..." />
            <TextField value={form.tags} onChange={(e) => setField('tags', e.target.value)} placeholder="Tags (comma separated): project, idea, bug" />
            <button onClick={handleAdd} disabled={!form.title.trim() || !form.body.trim()}
              className={cn('self-end rounded-lg border px-4 py-2 text-xs transition-all duration-200',
                form.title.trim() && form.body.trim() ? 'border-primary-container/50 bg-primary-container/10 text-primary hover:bg-primary-container/20'
                  : 'border-white/10 text-on-surface-variant/40 cursor-not-allowed')}>
              Save Note
            </button>
          </div>
        </GlassCard>
      )}

      <div className="mx-auto mb-5 max-w-xl">
        <SearchBox value={query} onChange={setQuery} placeholder="Search Knowledge Archive…" />
      </div>
      <FilterTabs tabs={tabs} active={category} onChange={setCategory} />

      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((note) => {
            const expanded = expandedId === note.id;
            return (
              <GlassCard key={note.id} hover onClick={() => setExpandedId(expanded ? null : note.id)}
                className={cn('cursor-pointer p-4', note.pinned && 'border-primary-container/40')}>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="mb-2 flex-1 text-sm font-semibold text-on-surface">{note.title}</h3>
                  <div className="flex shrink-0 items-center gap-1">
                    <button onClick={(e) => { e.stopPropagation(); togglePin(note); }}
                      className={cn('rounded p-1 transition-colors', note.pinned ? 'text-primary' : 'text-on-surface-variant/40 hover:text-primary')}
                      title={note.pinned ? 'Unpin' : 'Pin'}>
                      <Pin size={12} />
                    </button>
                    {expanded ? <ChevronUp size={14} className="text-on-surface-variant/60" /> : <ChevronDown size={14} className="text-on-surface-variant/40" />}
                  </div>
                </div>
                <div className="mb-2 flex flex-wrap gap-1.5">
                  {parseTags(note.tags).map((tag) => (
                    <span key={tag} className="rounded-full border border-primary-container/25 bg-primary-container/5 px-2 py-0.5 text-[10px] text-primary/70">{tag}</span>
                  ))}
                </div>
                <p className={cn('mb-2 text-xs text-on-surface-variant/70', !expanded && 'line-clamp-2')}>{note.body}</p>
                <div className="flex items-center justify-between">
                  <div className="text-[10px] text-on-surface-variant/40">{note.created_at ? new Date(note.created_at).toLocaleDateString() : ''}</div>
                  {expanded && (
                    <button onClick={(e) => { e.stopPropagation(); remove(note.id); }}
                      className="text-[10px] text-red-500/60 hover:text-red-400 transition-colors">Delete</button>
                  )}
                </div>
              </GlassCard>
            );
          })}
        </div>
      ) : (
        <EmptyState icon={Archive} title="No knowledge entries yet" hint='Click "Add Note" to save notes, decisions, and ideas.' />
      )}
    </div>
  );
}

export default ArchiveView;
