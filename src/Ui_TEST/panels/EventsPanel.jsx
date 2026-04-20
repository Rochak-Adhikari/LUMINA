import React, { useState, useEffect } from 'react';
import { CalendarDays, Plus, X, Check, Trash2 } from 'lucide-react';

const EventsPanel = ({ socket }) => {
    const [events, setEvents] = useState([]);
    const [showAddForm, setShowAddForm] = useState(false);
    const [formTitle, setFormTitle] = useState('');
    const [formDatetime, setFormDatetime] = useState('');
    const [formNotes, setFormNotes] = useState('');
    const [error, setError] = useState(null);

    useEffect(() => {
        socket.emit('list_events');

        const onList = (data) => setEvents(data || []);
        const onCreated = (evt) => setEvents(prev => [...prev, evt].sort((a, b) => a.datetime.localeCompare(b.datetime)));
        const onUpdated = (evt) => setEvents(prev => prev.map(e => e.id === evt.id ? evt : e));
        const onDeleted = (data) => setEvents(prev => prev.filter(e => e.id !== data.id));
        const onError = (data) => { if (data.panel === 'events') { setError(data.error); setTimeout(() => setError(null), 4000); } };

        socket.on('events_list', onList);
        socket.on('event_created', onCreated);
        socket.on('event_updated', onUpdated);
        socket.on('event_deleted', onDeleted);
        socket.on('panel_error', onError);

        return () => {
            socket.off('events_list', onList);
            socket.off('event_created', onCreated);
            socket.off('event_updated', onUpdated);
            socket.off('event_deleted', onDeleted);
            socket.off('panel_error', onError);
        };
    }, [socket]);

    const handleAdd = () => {
        if (!formTitle.trim() || !formDatetime) return;
        socket.emit('create_event', { title: formTitle.trim(), datetime: formDatetime, notes: formNotes.trim() });
        setFormTitle(''); setFormDatetime(''); setFormNotes(''); setShowAddForm(false);
    };

    const toggleComplete = (evt) => {
        socket.emit('update_event', { id: evt.id, completed: evt.completed ? 0 : 1 });
    };

    const handleDelete = (id) => {
        socket.emit('delete_event', { id });
    };

    // Group events by date
    const grouped = events.reduce((acc, evt) => {
        const dateKey = evt.datetime ? evt.datetime.split('T')[0] : 'Unknown';
        if (!acc[dateKey]) acc[dateKey] = [];
        acc[dateKey].push(evt);
        return acc;
    }, {});
    const sortedDates = Object.keys(grouped).sort();

    const formatDate = (dateStr) => {
        try {
            const d = new Date(dateStr + 'T00:00:00');
            const today = new Date(); today.setHours(0,0,0,0);
            const tomorrow = new Date(today); tomorrow.setDate(tomorrow.getDate() + 1);
            if (d.getTime() === today.getTime()) return 'TODAY';
            if (d.getTime() === tomorrow.getTime()) return 'TOMORROW';
            return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase();
        } catch { return dateStr; }
    };

    const formatTime = (dtStr) => {
        try {
            if (!dtStr.includes('T')) return '';
            return new Date(dtStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch { return ''; }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <h2 className="text-xl font-bold text-cyan-200 tracking-widest">Event Schedule</h2>
                <button onClick={() => setShowAddForm(!showAddForm)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 transition-all duration-200">
                    {showAddForm ? <X size={14} /> : <Plus size={14} />}
                    {showAddForm ? 'Cancel' : 'Add Event'}
                </button>
            </div>

            {/* Error toast */}
            {error && (
                <div className="mb-4 px-3 py-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-xs">{error}</div>
            )}

            {/* Add Event Form */}
            {showAddForm && (
                <div className="mb-6 border border-cyan-500/25 bg-black/30 backdrop-blur-sm rounded-xl p-5">
                    <h3 className="text-sm font-bold text-cyan-400 tracking-widest uppercase mb-4">New Event / Reminder</h3>
                    <div className="flex flex-col gap-3">
                        <input type="text" value={formTitle} onChange={e => setFormTitle(e.target.value)} placeholder="Event title"
                            className="bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all placeholder-cyan-800/50" />
                        <input type="datetime-local" value={formDatetime} onChange={e => setFormDatetime(e.target.value)}
                            className="bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all" />
                        <input type="text" value={formNotes} onChange={e => setFormNotes(e.target.value)} placeholder="Notes (optional)"
                            className="bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all placeholder-cyan-800/50" />
                        <button onClick={handleAdd} disabled={!formTitle.trim() || !formDatetime}
                            className={`self-end px-4 py-2 text-xs rounded-lg border transition-all duration-200 ${formTitle.trim() && formDatetime
                                ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20'
                                : 'border-gray-800/50 text-gray-700 cursor-not-allowed'}`}>
                            Save Event
                        </button>
                    </div>
                </div>
            )}

            {/* Timeline */}
            {sortedDates.length > 0 ? (
                <div className="relative">
                    <div className="absolute left-[14px] top-0 bottom-0 w-px bg-cyan-500/15" />

                    {sortedDates.map((dateKey) => (
                        <div key={dateKey} className="mb-8">
                            {/* Date marker */}
                            <div className="flex items-center gap-4 mb-4">
                                <div className="w-7 h-7 rounded-full border-2 border-cyan-500/50 bg-black shadow-[0_0_8px_rgba(6,182,212,0.3)] shrink-0 flex items-center justify-center z-10">
                                    <div className="w-2 h-2 rounded-full bg-cyan-400" />
                                </div>
                                <div className="text-xs text-cyan-400 tracking-widest font-bold">{formatDate(dateKey)}</div>
                            </div>

                            {/* Events for this date */}
                            <div className="ml-10 flex flex-col gap-3">
                                {grouped[dateKey].map((evt) => (
                                    <div key={evt.id}
                                        className={`border bg-black/30 backdrop-blur-sm rounded-xl p-4 transition-all duration-200 group ${
                                            evt.completed ? 'border-green-500/20 opacity-60' : 'border-cyan-500/15 hover:border-cyan-500/30 hover:bg-cyan-500/5'
                                        }`}>
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex-1">
                                                <h3 className={`text-sm font-semibold mb-1 transition-colors ${evt.completed ? 'text-green-400 line-through' : 'text-cyan-200 group-hover:text-cyan-100'}`}>{evt.title}</h3>
                                                {formatTime(evt.datetime) && <div className="text-[11px] text-cyan-600 mb-1 tracking-wide">{formatTime(evt.datetime)}</div>}
                                                {evt.notes && <p className="text-xs text-gray-400 leading-relaxed">{evt.notes}</p>}
                                            </div>
                                            <div className="flex items-center gap-1.5 shrink-0">
                                                <button onClick={() => toggleComplete(evt)}
                                                    className={`p-1.5 rounded-lg border transition-all ${evt.completed
                                                        ? 'border-green-500/30 text-green-400 bg-green-500/10'
                                                        : 'border-cyan-800/30 text-cyan-700 hover:text-cyan-400 hover:border-cyan-500/30'}`}
                                                    title={evt.completed ? 'Mark incomplete' : 'Mark complete'}>
                                                    <Check size={14} />
                                                </button>
                                                <button onClick={() => handleDelete(evt.id)}
                                                    className="p-1.5 rounded-lg border border-red-800/20 text-red-700 hover:text-red-400 hover:border-red-500/30 transition-all"
                                                    title="Delete">
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center py-16">
                    <div className="w-12 h-12 rounded-full border border-cyan-500/20 flex items-center justify-center mx-auto mb-4">
                        <CalendarDays size={20} className="text-cyan-700" />
                    </div>
                    <p className="text-cyan-600 text-sm mb-1">No events or reminders scheduled</p>
                    <p className="text-cyan-800 text-xs">Click "+ Add Event" to schedule events and reminders.</p>
                </div>
            )}
        </div>
    );
};

export default EventsPanel;
