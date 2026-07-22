// frontend/pages/Workspace/QuestsView.jsx — presentation only, state via useQuests
import React, { useState } from 'react';
import { Swords, Trash2 } from 'lucide-react';
import { GlassCard } from '../../components/ui';
import { useQuests } from '../../hooks/useWorkspace';
import {
  WorkspaceToolbar, ErrorToast, EmptyState, FilterTabs,
  TextField, TextArea, SelectField, FieldLabel,
} from '../../components/workspace';
import { cn } from '../../utils/cn';

const STATUS_TABS = [
  { id: 'active', label: 'Active' },
  { id: 'completed', label: 'Completed' },
  { id: 'side', label: 'Side Quests' },
];
const PRIORITY_BADGE = {
  high: 'text-red-400 border-red-500/30',
  medium: 'text-yellow-400 border-yellow-500/30',
  low: 'text-on-surface-variant border-white/20',
};

export function QuestsView() {
  const { items: quests, error, create, update, remove } = useQuests();
  const [filter, setFilter] = useState('active');
  const [selectedId, setSelectedId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium', status: 'active' });

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleAdd = () => {
    if (!form.title.trim()) return;
    create({ title: form.title.trim(), description: form.description.trim(), priority: form.priority, status: form.status });
    setForm({ title: '', description: '', priority: 'medium', status: 'active' });
    setShowForm(false);
  };

  const markComplete = (q) =>
    update({ id: q.id, status: q.status === 'completed' ? 'active' : 'completed', progress: q.status === 'completed' ? q.progress : 100 });

  const filtered = quests.filter((q) => q.status === filter);
  const selected = quests.find((q) => q.id === selectedId);
  const tabs = STATUS_TABS.map((t) => ({ ...t, count: quests.filter((q) => q.status === t.id).length }));

  return (
    <div>
      <WorkspaceToolbar
        title="Quests" subtitle="Track goals and progress" icon={Swords}
        addLabel="Add Quest" showForm={showForm} onToggleForm={() => setShowForm((s) => !s)}
      />
      <ErrorToast message={error} />

      {showForm && (
        <GlassCard className="mb-6 p-5">
          <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-primary/70">New Quest</h3>
          <div className="flex flex-col gap-3">
            <TextField value={form.title} onChange={(e) => setField('title', e.target.value)} placeholder="Quest title" />
            <TextArea value={form.description} onChange={(e) => setField('description', e.target.value)} placeholder="Description (optional)" />
            <div className="flex gap-3">
              <div className="flex-1">
                <FieldLabel>Priority</FieldLabel>
                <SelectField value={form.priority} onChange={(e) => setField('priority', e.target.value)}
                  options={[{ value: 'low', label: 'Low' }, { value: 'medium', label: 'Medium' }, { value: 'high', label: 'High' }]} />
              </div>
              <div className="flex-1">
                <FieldLabel>Category</FieldLabel>
                <SelectField value={form.status} onChange={(e) => setField('status', e.target.value)}
                  options={[{ value: 'active', label: 'Active' }, { value: 'side', label: 'Side Quest' }]} />
              </div>
            </div>
            <button onClick={handleAdd} disabled={!form.title.trim()}
              className={cn('self-end rounded-lg border px-4 py-2 text-xs transition-all duration-200',
                form.title.trim() ? 'border-primary-container/50 bg-primary-container/10 text-primary hover:bg-primary-container/20'
                  : 'border-white/10 text-on-surface-variant/40 cursor-not-allowed')}>
              Save Quest
            </button>
          </div>
        </GlassCard>
      )}

      <FilterTabs tabs={tabs} active={filter} onChange={(id) => { setFilter(id); setSelectedId(null); }} />

      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 flex flex-col gap-3">
            {filtered.map((quest) => (
              <button key={quest.id} onClick={() => setSelectedId(quest.id)}
                className={cn('text-left rounded-xl border p-4 transition-all duration-200',
                  selectedId === quest.id ? 'border-primary-container/40 bg-primary-container/5'
                    : 'border-white/10 bg-white/[0.02] hover:border-primary-container/30 hover:bg-white/[0.04]')}>
                <div className="mb-1 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-on-surface">{quest.title}</h3>
                  <span className={cn('rounded border px-1.5 py-0.5 text-[9px]', PRIORITY_BADGE[quest.priority] || PRIORITY_BADGE.medium)}>{quest.priority}</span>
                </div>
                {quest.description && <p className="mb-3 line-clamp-2 text-xs text-on-surface-variant/70">{quest.description}</p>}
                <div className="flex items-center gap-2">
                  <div className="h-1.5 flex-1 rounded-full bg-primary-container/10">
                    <div className="h-full rounded-full bg-primary-container transition-all duration-500" style={{ width: `${quest.progress || 0}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-on-surface-variant/60">{quest.progress || 0}%</span>
                </div>
              </button>
            ))}
          </div>

          <div className="lg:col-span-2">
            {selected ? (
              <GlassCard className="p-6">
                <div className="mb-4 flex items-start justify-between">
                  <div>
                    <h3 className="mb-1 text-lg font-bold text-primary">{selected.title}</h3>
                    <span className={cn('rounded border px-2 py-0.5 text-[10px]', PRIORITY_BADGE[selected.priority] || PRIORITY_BADGE.medium)}>{selected.priority} priority</span>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => markComplete(selected)}
                      className={cn('rounded-lg border px-3 py-1.5 text-xs transition-all',
                        selected.status === 'completed' ? 'border-primary-container/30 text-primary hover:bg-primary-container/10'
                          : 'border-green-500/30 text-green-400 hover:bg-green-500/10')}>
                      {selected.status === 'completed' ? 'Reopen' : 'Complete'}
                    </button>
                    <button onClick={() => remove(selected.id)}
                      className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 transition-all">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                {selected.description && <p className="mb-5 text-sm text-on-surface-variant/80">{selected.description}</p>}
                <div className="flex items-center gap-3">
                  <div className="h-2 flex-1 rounded-full bg-primary-container/10">
                    <div className="h-full rounded-full bg-primary-container transition-all duration-500" style={{ width: `${selected.progress || 0}%` }} />
                  </div>
                  <span className="font-mono text-sm text-primary">{selected.progress || 0}%</span>
                </div>
                <div className="mt-4 text-[10px] text-on-surface-variant/40">
                  Created: {selected.created_at ? new Date(selected.created_at).toLocaleString() : 'Unknown'}
                </div>
              </GlassCard>
            ) : (
              <GlassCard className="flex h-full min-h-[200px] items-center justify-center p-8">
                <div className="text-center">
                  <Swords size={24} className="mx-auto mb-2 text-on-surface-variant/40" />
                  <p className="text-sm text-on-surface-variant/50">Select a quest to view details</p>
                </div>
              </GlassCard>
            )}
          </div>
        </div>
      ) : (
        <EmptyState icon={Swords} title="No quests in this category" hint='Click "Add Quest" to create quests and track progress.' />
      )}
    </div>
  );
}

export default QuestsView;
