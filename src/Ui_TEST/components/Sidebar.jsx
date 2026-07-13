import { Home, Globe, Sparkles, CalendarDays, Archive, Settings } from 'lucide-react';

const Sidebar = ({ activePanel, onNavigate }) => {
    const NAV_ITEMS = [
        { id: 'home', label: 'Home', icon: Home },
        { id: 'browser', label: 'Browser', icon: Globe },
        { id: 'features', label: 'Intelligence', icon: Sparkles },
        { id: 'events', label: 'Timeline', icon: CalendarDays },
        { id: 'archive', label: 'Archive', icon: Archive },
        { id: 'settings', label: 'Settings', icon: Settings },
    ];

    return (
        <aside className="fixed left-6 top-1/2 -translate-y-1/2 w-20 rounded-full backdrop-blur-3xl bg-white/5 border border-white/10 shadow-[0_0_40px_rgba(60,215,255,0.1)] flex flex-col items-center py-8 space-y-6 z-50 transition-all duration-300">
            <div className="flex flex-col gap-6 w-full items-center">
                {NAV_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const isActive = activePanel === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => onNavigate(item.id)}
                            className={`group relative p-4 rounded-full flex justify-center items-center transition-all duration-500 hover:scale-115 active:scale-90 ${
                                isActive
                                    ? 'bg-primary-container/20 text-primary shadow-[0_0_20px_rgba(0,212,255,0.35)] border border-primary-container/40'
                                    : 'text-on-surface-variant hover:bg-white/10 hover:text-primary'
                            }`}
                        >
                            <Icon size={22} className={isActive ? 'stroke-[2.5px]' : 'stroke-[1.5px]'} />
                            
                            {/* Hover tooltip */}
                            <div className="absolute left-full ml-4 px-3 py-1.5 rounded-lg glass-level-2 text-on-surface opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap text-xs font-mono tracking-wider border border-white/5 shadow-xl">
                                {item.label}
                            </div>
                        </button>
                    );
                })}
            </div>
        </aside>
    );
};

export default Sidebar;
