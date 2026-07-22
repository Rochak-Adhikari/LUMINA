// frontend/pages/Workspace/EventsView.jsx — presentation only, state via useEvents
import React, { useState } from 'react';
import { CalendarDays, Check, Trash2 } from 'lucide-react';
import { GlassCard } from '../../components/ui';
import { useEvents } from '../../hooks/useWorkspace';
import {
  WorkspaceToolbar, ErrorToast, EmptyState, TextField, DateTimeField,
} from '../../components/workspace';
import { cn } from '../../utils/cn';

function formatDate(dateStr) {
  try {
    const d = new Date(dateStr + 'T00:00:00');
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today); tomorrow.setDate(tomorrow.getDate() + 1);
    if (d.getTime() === today.getTime()) return 'TODAY';
    if (d.getTime() === tomorrow.getTime()) return 'TOMORROW';
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase();
  } catch { return dateStr; }
}
function formatTime(dtStr) {
  try {
    if (!dtStr.includes('T')) return '';
    return new Date(dtStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

export function EventsView() {
  const { items: events, error, create, update, remove } = useEvents();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', datetime: '', notes: '' });
  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleAdd = () => {
    if (!form.title.trim() || !form.datetime) return;
    create({ title: form.title.trim(), datetime: form.datetime, notes: form.notes.trim() });
    setForm({ title: '', datetime: '', notes: '' });
    setShowForm(false);
  };
  const toggleComplete = (evt) => update({ id: evt.id, completed: evt.completed ? 0 : 1 });

  const grouped = events.reduce((acc, evt) => {
    const key = evt.datetime ? evt.datetime.split('T')[0] : 'Unknown';
    (acc[key] = acc[key] || []).push(evt);
    return acc;
  }, {});
  const sortedDates = Object.keys(grouped).sort();

  return (
    <div>
      <WorkspaceToolbar
        title="Event Schedule" subtitle="Events and reminders" icon={CalendarDays}
        addLabel="Add Event" showForm={showForm} onToggleForm={() => setShowForm((s) => !s)}
      />
      <ErrorToast message={error} />

      {showForm && (
        <GlassCard className="mb-6 p-5">
          <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-primary/70">New Event / Reminder</h3>
          <div className="flex flex-col gap-3">
            <TextField value={form.title} onChange={(e) => setField('title', e.target.value)} placeholder="Event title" />
            <DateTimeField value={form.datetime} onChange={(e) => setField('datetime', e.target.value)} />
            <TextField value={form.notes} onChange={(e) => setField('notes', e.target.value)} placeholder="Notes (optional)" />
            <button onClick={handleAdd} disabled={!form.title.trim() || !form.datetime}
              className={cn('self-end rounded-lg border px-4 py-2 text-xs transition-all duration-200',
                form.title.trim() && form.datetime ? 'border-primary-container/50 bg-primary-container/10 text-primary hover:bg-primary-container/20'
                  : 'border-white/10 text-on-surface-variant/40 cursor-not-allowed')}>
              Save Event
            </button>
          </div>
        </GlassCard>
      )}

      {sortedDates.length > 0 ? (
        <div className="relative">
          <div className="absolute left-[14px] top-0 bottom-0 w-px bg-primary-container/15" />
          {sortedDates.map((dateKey) => (
            <div key={dateKey} className="mb-8">
              <div className="mb-4 flex items-center gap-4">
                <div className="z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-primary-container/50 bg-[#030405] shadow-[0_0_8px_rgba(6,182,212,0.3)]">
                  <div className="h-2 w-2 rounded-full bg-primary" />
                </div>
                <div className="text-xs font-bold tracking-widest text-primary">{formatDate(dateKey)}</div>
              </div>
              <div className="ml-10 flex flex-col gap-3">
                {grouped[dateKey].map((evt) => (
                  <GlassCard key={evt.id} className={cn('p-4', evt.completed && 'opacity-60')}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <h3 className={cn('mb-1 text-sm font-semibold', evt.completed ? 'text-green-400 line-through' : 'text-on-surface')}>{evt.title}</h3>
                        {formatTime(evt.datetime) && <div className="mb-1 text-[11px] tracking-wide text-on-surface-variant/60">{formatTime(evt.datetime)}</div>}
                        {evt.notes && <p className="text-xs text-on-surface-variant/70">{evt.notes}</p>}
                      </div>
                      <div className="flex shrink-0 items-center gap-1.5">
                        <button onClick={() => toggleComplete(evt)}
                          className={cn('rounded-lg border p-1.5 transition-all',
                            evt.completed ? 'border-green-500/30 bg-green-500/10 text-green-400'
                              : 'border-white/10 text-on-surface-variant/60 hover:border-primary-container/30 hover:text-primary')}
                          title={evt.completed ? 'Mark incomplete' : 'Mark complete'}>
                          <Check size={14} />
                        </button>
                        <button onClick={() => remove(evt.id)}
                          className="rounded-lg border border-red-500/20 p-1.5 text-red-500/70 hover:border-red-500/30 hover:text-red-400 transition-all" title="Delete">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </GlassCard>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon={CalendarDays} title="No events or reminders scheduled" hint='Click "Add Event" to schedule events and reminders.' />
      )}
    </div>
  );
}

export default EventsView;
