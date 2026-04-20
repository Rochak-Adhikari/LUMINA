import React, { useState, useEffect } from 'react';
import { Search, Plus, X, Pin, ChevronDown, ChevronUp } from 'lucide-react';

const CATEGORIES = ['All', 'project', 'study', 'health', 'idea', 'bug', 'fix', 'personal'];

const KnowledgeArchivePanel = ({ socket }) => {
    const [notes, setNotes] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState('All');
    const [expandedId, setExpandedId] = useState(null);
    const [showAddForm, setShowAddForm] = useState(false);
    const [formTitle, setFormTitle] = useState('');
    const [formBody, setFormBody] = useState('');
    const [formTags, setFormTags] = useState('');
    const [error, setError] = useState(null);

    useEffect(() => {
        socket.emit('list_archive_notes');

        const onList = (data) => setNotes(data || []);
        const onCreated = (note) => setNotes(prev => [note, ...prev]);
        const onUpdated = (note) => setNotes(prev => prev.map(n => n.id === note.id ? note : n));
        const onDeleted = (data) => setNotes(prev => prev.filter(n => n.id !== data.id));
        const onError = (data) => { if (data.panel === 'archive') { setError(data.error); setTimeout(() => setError(null), 4000); } };

        socket.on('archive_notes_list', onList);
        socket.on('archive_note_created', onCreated);
        socket.on('archive_note_updated', onUpdated);
        socket.on('archive_note_deleted', onDeleted);
        socket.on('panel_error', onError);

        return () => {
            socket.off('archive_notes_list', onList);
            socket.off('archive_note_created', onCreated);
            socket.off('archive_note_updated', onUpdated);
            socket.off('archive_note_deleted', onDeleted);
            socket.off('panel_error', onError);
        };
    }, [socket]);

    const handleAdd = () => {
        if (!formTitle.trim() || !formBody.trim()) return;
        socket.emit('create_archive_note', { title: formTitle.trim(), body: formBody.trim(), tags: formTags.trim() });
        setFormTitle(''); setFormBody(''); setFormTags(''); setShowAddForm(false);
    };

    const togglePin = (note) => {
        socket.emit('update_archive_note', { id: note.id, pinned: note.pinned ? 0 : 1 });
    };

    const handleDelete = (id) => {
        socket.emit('delete_archive_note', { id });
    };

    const parseTags = (tagsStr) => tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];

    const filtered = notes.filter(note => {
        const matchesSearch = !searchQuery || note.title.toLowerCase().includes(searchQuery.toLowerCase()) || note.body.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesCategory = activeCategory === 'All' || (note.tags && note.tags.toLowerCase().includes(activeCategory.toLowerCase()));
        return matchesSearch && matchesCategory;
    });

    return (
        <div className="p-6 max-w-6xl mx-auto">
            {/* Header row */}
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-cyan-200 tracking-widest">Knowledge Archive</h2>
                <button
                    onClick={() => setShowAddForm(!showAddForm)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 transition-all duration-200"
                >
                    {showAddForm ? <X size={14} /> : <Plus size={14} />}
                    {showAddForm ? 'Cancel' : 'Add Note'}
                </button>
            </div>

            {/* Error toast */}
            {error && (
                <div className="mb-4 px-3 py-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-xs">{error}</div>
            )}

            {/* Add Note Form */}
            {showAddForm && (
                <div className="mb-6 border border-cyan-500/25 bg-black/30 backdrop-blur-sm rounded-xl p-5">
                    <h3 className="text-sm font-bold text-cyan-400 tracking-widest uppercase mb-4">New Note</h3>
                    <div className="flex flex-col gap-3">
                        <input type="text" value={formTitle} onChange={e => setFormTitle(e.target.value)} placeholder="Title"
                            className="bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all placeholder-cyan-800/50" />
                        <textarea value={formBody} onChange={e => setFormBody(e.target.value)} placeholder="Note body..." rows={4}
                            className="bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all placeholder-cyan-800/50 resize-none" />
                        <input type="text" value={formTags} onChange={e => setFormTags(e.target.value)} placeholder="Tags (comma separated): project, idea, bug"
                            className="bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all placeholder-cyan-800/50" />
                        <button onClick={handleAdd} disabled={!formTitle.trim() || !formBody.trim()}
                            className={`self-end px-4 py-2 text-xs rounded-lg border transition-all duration-200 ${formTitle.trim() && formBody.trim()
                                ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20'
                                : 'border-gray-800/50 text-gray-700 cursor-not-allowed'}`}>
                            Save Note
                        </button>
                    </div>
                </div>
            )}

            {/* Search Bar */}
            <div className="max-w-xl mx-auto mb-5">
                <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-700" />
                    <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search Knowledge Archive..."
                        className="w-full bg-black/40 border border-cyan-700/30 rounded-lg pl-10 pr-4 py-2.5 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all placeholder-cyan-800/50 backdrop-blur-sm" />
                </div>
            </div>

            {/* Category Tabs */}
            <div className="flex justify-center gap-2 mb-6 flex-wrap">
                {CATEGORIES.map(cat => (
                    <button key={cat} onClick={() => setActiveCategory(cat)}
                        className={`px-3 py-1 text-xs rounded-md border transition-all duration-200 ${
                            activeCategory === cat
                                ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.1)]'
                                : 'border-cyan-800/30 text-cyan-600 hover:border-cyan-500/30 hover:text-cyan-400'
                        }`}>
                        {cat === 'All' ? 'All' : cat}
                    </button>
                ))}
            </div>

            {/* Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filtered.map((note) => (
                    <div key={note.id}
                        onClick={() => setExpandedId(expandedId === note.id ? null : note.id)}
                        className={`group border bg-black/30 backdrop-blur-sm rounded-xl p-4 transition-all duration-200 cursor-pointer ${
                            note.pinned ? 'border-cyan-500/40 shadow-[0_0_8px_rgba(6,182,212,0.08)]' : 'border-cyan-500/15 hover:border-cyan-500/30 hover:bg-cyan-500/5'
                        }`}>
                        <div className="flex items-start justify-between gap-2">
                            <h3 className="text-sm font-semibold text-cyan-200 mb-2 group-hover:text-cyan-100 transition-colors flex-1">{note.title}</h3>
                            <div className="flex items-center gap-1 shrink-0">
                                <button onClick={(e) => { e.stopPropagation(); togglePin(note); }}
                                    className={`p-1 rounded transition-colors ${note.pinned ? 'text-cyan-400' : 'text-cyan-800 hover:text-cyan-500'}`}
                                    title={note.pinned ? 'Unpin' : 'Pin'}>
                                    <Pin size={12} />
                                </button>
                                {expandedId === note.id ? <ChevronUp size={14} className="text-cyan-600" /> : <ChevronDown size={14} className="text-cyan-700" />}
                            </div>
                        </div>
                        <div className="flex gap-1.5 mb-2 flex-wrap">
                            {parseTags(note.tags).map(tag => (
                                <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full border border-cyan-500/25 text-cyan-500 bg-cyan-500/5">{tag}</span>
                            ))}
                        </div>
                        <p className={`text-xs text-gray-400 leading-relaxed mb-2 ${expandedId === note.id ? '' : 'line-clamp-2'}`}>{note.body}</p>
                        <div className="flex items-center justify-between">
                            <div className="text-[10px] text-cyan-700">{note.created_at ? new Date(note.created_at).toLocaleDateString() : ''}</div>
                            {expandedId === note.id && (
                                <button onClick={(e) => { e.stopPropagation(); handleDelete(note.id); }}
                                    className="text-[10px] text-red-500/60 hover:text-red-400 transition-colors">Delete</button>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {filtered.length === 0 && (
                <div className="text-center py-16">
                    <div className="w-12 h-12 rounded-full border border-cyan-500/20 flex items-center justify-center mx-auto mb-4">
                        <Search size={20} className="text-cyan-700" />
                    </div>
                    <p className="text-cyan-600 text-sm mb-1">No knowledge entries yet</p>
                    <p className="text-cyan-800 text-xs">Click "+ Add Note" to save important notes, decisions, and ideas.</p>
                </div>
            )}
        </div>
    );
};

export default KnowledgeArchivePanel;
