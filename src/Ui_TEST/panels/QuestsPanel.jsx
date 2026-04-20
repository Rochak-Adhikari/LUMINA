import React, { useState, useEffect } from 'react';
import { Swords, Plus, X, Trash2 } from 'lucide-react';

const STATUS_TABS = [
    { id: 'active', label: 'Active', color: 'cyan' },
    { id: 'completed', label: 'Completed', color: 'green' },
    { id: 'side', label: 'Side Quests', color: 'purple' },
];

const colorMap = {
    cyan: { border: 'border-cyan-500/30', bg: 'bg-cyan-500/5', text: 'text-cyan-300', textMuted: 'text-cyan-600', bar: 'bg-cyan-500', barBg: 'bg-cyan-500/10', glow: 'shadow-[0_0_10px_rgba(6,182,212,0.08)]' },
    green: { border: 'border-green-500/30', bg: 'bg-green-500/5', text: 'text-green-300', textMuted: 'text-green-600', bar: 'bg-green-500', barBg: 'bg-green-500/10', glow: 'shadow-[0_0_10px_rgba(34,197,94,0.08)]' },
    purple: { border: 'border-purple-500/30', bg: 'bg-purple-500/5', text: 'text-purple-300', textMuted: 'text-purple-600', bar: 'bg-purple-500', barBg: 'bg-purple-500/10', glow: 'shadow-[0_0_10px_rgba(168,85,247,0.08)]' },
};

const priorityBadge = { high: 'text-red-400 border-red-500/30', medium: 'text-yellow-400 border-yellow-500/30', low: 'text-gray-400 border-gray-500/30' };

const QuestsPanel = ({ socket }) => {
    const [quests, setQuests] = useState([]);
    const [activeFilter, setActiveFilter] = useState('active');
    const [selectedId, setSelectedId] = useState(null);
    const [showAddForm, setShowAddForm] = useState(false);
    const [formTitle, setFormTitle] = useState('');
    const [formDesc, setFormDesc] = useState('');
    const [formPriority, setFormPriority] = useState('medium');
    const [formStatus, setFormStatus] = useState('active');
    const [error, setError] = useState(null);

    useEffect(() => {
        socket.emit('list_quests');

        const onList = (data) => setQuests(data || []);
        const onCreated = (q) => setQuests(prev => [q, ...prev]);
        const onUpdated = (q) => setQuests(prev => prev.map(x => x.id === q.id ? q : x));
        const onDeleted = (data) => { setQuests(prev => prev.filter(x => x.id !== data.id)); if (selectedId === data.id) setSelectedId(null); };
        const onError = (data) => { if (data.panel === 'quests') { setError(data.error); setTimeout(() => setError(null), 4000); } };

        socket.on('quests_list', onList);
        socket.on('quest_created', onCreated);
        socket.on('quest_updated', onUpdated);
        socket.on('quest_deleted', onDeleted);
        socket.on('panel_error', onError);

        return () => {
            socket.off('quests_list', onList);
            socket.off('quest_created', onCreated);
            socket.off('quest_updated', onUpdated);
            socket.off('quest_deleted', onDeleted);
            socket.off('panel_error', onError);
        };
    }, [socket]);

    const handleAdd = () => {
        if (!formTitle.trim()) return;
        socket.emit('create_quest', { title: formTitle.trim(), description: formDesc.trim(), priority: formPriority, status: formStatus });
        setFormTitle(''); setFormDesc(''); setFormPriority('medium'); setFormStatus('active'); setShowAddForm(false);
    };

    const markComplete = (q) => {
        socket.emit('update_quest', { id: q.id, status: q.status === 'completed' ? 'active' : 'completed', progress: q.status === 'completed' ? q.progress : 100 });
    };

    const handleDelete = (id) => {
        socket.emit('delete_quest', { id });
    };

    const filteredQuests = quests.filter(q => q.status === activeFilter);
    const selectedQuest = quests.find(q => q.id === selectedId);
    const tabColor = STATUS_TABS.find(t => t.id === activeFilter)?.color || 'cyan';
    const c = colorMap[tabColor];

    return (
        <div className="p-6 max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-cyan-200 tracking-widest">Quests</h2>
                <button onClick={() => setShowAddForm(!showAddForm)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 transition-all duration-200">
                    {showAddForm ? <X size={14} /> : <Plus size={14} />}
                    {showAddForm ? 'Cancel' : 'Add Quest'}
                </button>
            </div>

            {/* Error toast */}
            {error && (
                <div className="mb-4 px-3 py-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-xs">{error}</div>
            )}

            {/* Add Quest Form */}
            {showAddForm && (
                <div className="mb-6 border border-cyan-500/25 bg-black/30 backdrop-blur-sm rounded-xl p-5">
                    <h3 className="text-sm font-bold text-cyan-400 tracking-widest uppercase mb-4">New Quest</h3>
                    <div className="flex flex-col gap-3">
                        <input type="text" value={formTitle} onChange={e => setFormTitle(e.target.value)} placeholder="Quest title"
                            className="bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all placeholder-cyan-800/50" />
                        <textarea value={formDesc} onChange={e => setFormDesc(e.target.value)} placeholder="Description (optional)" rows={3}
                            className="bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all placeholder-cyan-800/50 resize-none" />
                        <div className="flex gap-3">
                            <div className="flex-1">
                                <span className="text-[10px] text-cyan-600 block mb-1">Priority</span>
                                <select value={formPriority} onChange={e => setFormPriority(e.target.value)}
                                    className="w-full bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-xs text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all">
                                    <option value="low">Low</option>
                                    <option value="medium">Medium</option>
                                    <option value="high">High</option>
                                </select>
                            </div>
                            <div className="flex-1">
                                <span className="text-[10px] text-cyan-600 block mb-1">Category</span>
                                <select value={formStatus} onChange={e => setFormStatus(e.target.value)}
                                    className="w-full bg-black/40 border border-cyan-700/30 rounded-lg px-3 py-2 text-xs text-cyan-50 focus:outline-none focus:border-cyan-400 transition-all">
                                    <option value="active">Active</option>
                                    <option value="side">Side Quest</option>
                                </select>
                            </div>
                        </div>
                        <button onClick={handleAdd} disabled={!formTitle.trim()}
                            className={`self-end px-4 py-2 text-xs rounded-lg border transition-all duration-200 ${formTitle.trim()
                                ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20'
                                : 'border-gray-800/50 text-gray-700 cursor-not-allowed'}`}>
                            Save Quest
                        </button>
                    </div>
                </div>
            )}

            {/* Filter Tabs */}
            <div className="flex justify-center gap-2 mb-6">
                {STATUS_TABS.map(tab => {
                    const tc = colorMap[tab.color];
                    const isActive = activeFilter === tab.id;
                    const count = quests.filter(q => q.status === tab.id).length;
                    return (
                        <button key={tab.id} onClick={() => { setActiveFilter(tab.id); setSelectedId(null); }}
                            className={`px-3 py-1 text-xs rounded-md border transition-all duration-200 ${
                                isActive ? `${tc.border} ${tc.bg} ${tc.text} ${tc.glow}` : 'border-cyan-800/30 text-cyan-600 hover:border-cyan-500/30 hover:text-cyan-400'
                            }`}>
                            {tab.label} ({count})
                        </button>
                    );
                })}
            </div>

            {/* Quest list + detail */}
            {filteredQuests.length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-1 flex flex-col gap-3">
                        {filteredQuests.map((quest) => (
                            <button key={quest.id} onClick={() => setSelectedId(quest.id)}
                                className={`text-left border rounded-xl p-4 transition-all duration-200 group ${
                                    selectedId === quest.id ? `${c.border} ${c.bg} ${c.glow}` : 'border-cyan-500/15 bg-black/30 hover:border-cyan-500/30 hover:bg-cyan-500/5'
                                }`}>
                                <div className="flex items-center justify-between mb-1">
                                    <h3 className={`text-sm font-semibold transition-colors ${selectedId === quest.id ? c.text : 'text-cyan-200 group-hover:text-cyan-100'}`}>{quest.title}</h3>
                                    <span className={`text-[9px] px-1.5 py-0.5 rounded border ${priorityBadge[quest.priority] || priorityBadge.medium}`}>{quest.priority}</span>
                                </div>
                                {quest.description && <p className="text-xs text-gray-400 leading-relaxed mb-3 line-clamp-2">{quest.description}</p>}
                                <div className="flex items-center gap-2">
                                    <div className={`flex-1 h-1.5 rounded-full ${c.barBg}`}>
                                        <div className={`h-full rounded-full ${c.bar} transition-all duration-500`} style={{ width: `${quest.progress || 0}%` }} />
                                    </div>
                                    <span className={`text-[10px] font-mono ${c.textMuted}`}>{quest.progress || 0}%</span>
                                </div>
                            </button>
                        ))}
                    </div>

                    <div className="lg:col-span-2">
                        {selectedQuest ? (
                            <div className={`border rounded-xl p-6 ${c.border} bg-black/20 backdrop-blur-sm`}>
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <h3 className={`text-lg font-bold ${c.text} mb-1`}>{selectedQuest.title}</h3>
                                        <span className={`text-[10px] px-2 py-0.5 rounded border ${priorityBadge[selectedQuest.priority] || priorityBadge.medium}`}>{selectedQuest.priority} priority</span>
                                    </div>
                                    <div className="flex gap-2">
                                        <button onClick={() => markComplete(selectedQuest)}
                                            className={`px-3 py-1.5 text-xs rounded-lg border transition-all ${selectedQuest.status === 'completed'
                                                ? 'border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10' : 'border-green-500/30 text-green-400 hover:bg-green-500/10'}`}>
                                            {selectedQuest.status === 'completed' ? 'Reopen' : 'Complete'}
                                        </button>
                                        <button onClick={() => handleDelete(selectedQuest.id)}
                                            className="px-3 py-1.5 text-xs rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-all">
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </div>
                                {selectedQuest.description && <p className="text-sm text-gray-400 mb-5">{selectedQuest.description}</p>}
                                <div className="flex items-center gap-3">
                                    <div className={`flex-1 h-2 rounded-full ${c.barBg}`}>
                                        <div className={`h-full rounded-full ${c.bar} transition-all duration-500`} style={{ width: `${selectedQuest.progress || 0}%` }} />
                                    </div>
                                    <span className={`text-sm font-mono ${c.text}`}>{selectedQuest.progress || 0}%</span>
                                </div>
                                <div className="text-[10px] text-cyan-700 mt-4">Created: {selectedQuest.created_at ? new Date(selectedQuest.created_at).toLocaleString() : 'Unknown'}</div>
                            </div>
                        ) : (
                            <div className="border border-cyan-500/10 bg-black/20 rounded-xl p-8 flex items-center justify-center h-full min-h-[200px]">
                                <div className="text-center">
                                    <Swords size={24} className="text-cyan-700 mx-auto mb-2" />
                                    <p className="text-sm text-cyan-700">Select a quest to view details</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ) : (
                <div className="text-center py-16">
                    <div className="w-12 h-12 rounded-full border border-cyan-500/20 flex items-center justify-center mx-auto mb-4">
                        <Swords size={20} className="text-cyan-700" />
                    </div>
                    <p className="text-cyan-600 text-sm mb-1">No quests in this category</p>
                    <p className="text-cyan-800 text-xs">Click "+ Add Quest" to create quests and track progress.</p>
                </div>
            )}
        </div>
    );
};

export default QuestsPanel;
