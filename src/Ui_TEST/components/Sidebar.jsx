import React from 'react';
import { Archive, CalendarDays, Swords, Home, Settings } from 'lucide-react';

const NAV_ITEMS = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'archive', label: 'Knowledge Archive', icon: Archive },
    { id: 'events', label: 'Events / Reminders', icon: CalendarDays },
    { id: 'quests', label: 'Quests', icon: Swords },
    { id: 'settings', label: 'Settings', icon: Settings },
];

const Sidebar = ({ isOpen, activePanel, onNavigate }) => {
    return (
        <div
            className={`shrink-0 flex flex-col border-r border-cyan-500/15 bg-black/70 backdrop-blur-xl transition-all duration-300 ease-in-out overflow-hidden ${
                isOpen ? 'w-56' : 'w-0'
            }`}
        >
            {/* Sidebar Content — only rendered when open to avoid layout jank */}
            <div className={`flex flex-col h-full w-56 ${isOpen ? 'opacity-100' : 'opacity-0'} transition-opacity duration-200`}>
                {/* LUNA badge */}
                <div className="px-5 py-4 border-b border-cyan-500/10">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full border border-cyan-500/40 flex items-center justify-center shadow-[0_0_12px_rgba(6,182,212,0.15)]">
                            <span className="text-xs font-bold text-cyan-400 tracking-wider">L</span>
                        </div>
                        <div>
                            <div className="text-sm font-bold text-cyan-300 tracking-widest">LUNA</div>
                            <div className="text-[9px] text-cyan-700 tracking-wide">COMPANION SYSTEM</div>
                        </div>
                    </div>
                </div>

                {/* Nav Items */}
                <nav className="flex-1 py-3 px-2 flex flex-col gap-1">
                    {NAV_ITEMS.map((item) => {
                        const Icon = item.icon;
                        const isActive = activePanel === item.id;
                        return (
                            <button
                                key={item.id}
                                onClick={() => onNavigate(item.id)}
                                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-200 group w-full ${
                                    isActive
                                        ? 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.08)]'
                                        : 'border border-transparent text-cyan-600 hover:text-cyan-400 hover:bg-cyan-500/5 hover:border-cyan-500/15'
                                }`}
                            >
                                <Icon size={18} className={`shrink-0 transition-colors ${isActive ? 'text-cyan-400' : 'text-cyan-700 group-hover:text-cyan-500'}`} />
                                <span className="text-xs font-medium tracking-wide truncate">{item.label}</span>
                                {isActive && (
                                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.6)]" />
                                )}
                            </button>
                        );
                    })}
                </nav>

                {/* Bottom section */}
                <div className="px-4 py-3 border-t border-cyan-500/10">
                    <div className="text-[9px] text-cyan-800 tracking-wider text-center">
                        LUMINA v2.0
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
