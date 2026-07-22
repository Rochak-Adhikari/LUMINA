import React, { useState, useEffect, useRef } from 'react';
import { ChevronLeft, ChevronRight, RotateCw, Plus, X, Bookmark, Download, Settings, Terminal, Shield, Sparkles, Send, Mic, MicOff } from 'lucide-react';
import Visualizer from '../../components/Visualizer';

const { ipcRenderer } = window.require('electron');

const BrowserWorkspacePanel = ({ socket, openUrl, aiAudioData, isConnected, isMuted, messages, toggleMute, handleSendClick, handleSendKey, inputValue, setInputValue, messagesEndRef, audioAmp }) => {
    const placeholderRef = useRef(null);
    // Flicker fix: coalesce rapid updateBounds() calls (ResizeObserver + mount
    // timers + tab/nav effects) into a single rAF-scheduled send, and skip the
    // IPC entirely when geometry is unchanged. Prevents the BrowserView from
    // being repositioned 8+ times in a burst on panel open.
    const boundsRafRef = useRef(0);
    const lastBoundsRef = useRef(null);
    // Live refs so the mount-scoped ([]) IPC listeners read current tab state
    // without a stale closure (crash/stale recovery needs the latest URL).
    const tabsRef = useRef(null);
    const activeTabIdRef = useRef(null);

    // Tab State — persisted across restarts (restore tabs + active tab + URLs).
    const [tabs, setTabs] = useState(() => {
        try {
            const saved = JSON.parse(localStorage.getItem('lumina_browser_tabs'));
            if (Array.isArray(saved) && saved.length) {
                // reset transient loading flags on restore
                return saved.map(t => ({ ...t, loading: false }));
            }
        } catch { /* fall through to default */ }
        return [{ id: 'tab-default', title: 'Google', url: 'https://www.google.com', loading: false, favicon: null }];
    });
    const [activeTabId, setActiveTabId] = useState(() => {
        try {
            const saved = localStorage.getItem('lumina_browser_active_tab');
            const savedTabs = JSON.parse(localStorage.getItem('lumina_browser_tabs'));
            if (saved && Array.isArray(savedTabs) && savedTabs.some(t => t.id === saved)) return saved;
        } catch { /* ignore */ }
        return 'tab-default';
    });
    const [inputUrl, setInputUrl] = useState(() => {
        try {
            const savedTabs = JSON.parse(localStorage.getItem('lumina_browser_tabs'));
            const savedActive = localStorage.getItem('lumina_browser_active_tab');
            const t = Array.isArray(savedTabs) && savedTabs.find(x => x.id === savedActive);
            if (t && t.url) return t.url;
        } catch { /* ignore */ }
        return 'https://www.google.com';
    });

    // Bookmarks & Downloads
    const [bookmarks, setBookmarks] = useState(() => {
        try {
            return JSON.parse(localStorage.getItem('lumina_bookmarks')) || [
                { title: 'Google', url: 'https://www.google.com' },
                { title: 'GitHub', url: 'https://github.com' },
                { title: 'YouTube', url: 'https://youtube.com' }
            ];
        } catch { return []; }
    });
    const [downloads, setDownloads] = useState([]);
    const [showDownloads, setShowDownloads] = useState(false);

    // Persist bookmarks
    useEffect(() => {
        localStorage.setItem('lumina_bookmarks', JSON.stringify(bookmarks));
    }, [bookmarks]);

    // Persist tabs + active tab so they restore after an app restart. Store only
    // serialisable fields (drop transient loading flag).
    useEffect(() => {
        try {
            const slim = tabs.map(({ id, title, url, favicon }) => ({ id, title, url, favicon }));
            localStorage.setItem('lumina_browser_tabs', JSON.stringify(slim));
            localStorage.setItem('lumina_browser_active_tab', activeTabId);
        } catch { /* storage full / unavailable — non-fatal */ }
    }, [tabs, activeTabId]);

    // Keep live refs current for the mount-scoped recovery listeners.
    useEffect(() => { tabsRef.current = tabs; }, [tabs]);
    useEffect(() => { activeTabIdRef.current = activeTabId; }, [activeTabId]);

    // Active tab change sync
    useEffect(() => {
        const activeTab = tabs.find(t => t.id === activeTabId);
        if (activeTab) {
            setInputUrl(activeTab.url);
            ipcRenderer.send('browser-switch-tab', { tabId: activeTabId });
            setTimeout(updateBounds, 80);
        }
    }, [activeTabId]);

    // Backend browser_open → load URL into the embedded browser (active tab).
    // Keyed on openUrl.ts so repeated opens of the same URL still navigate.
    // YouTube search URLs trigger the in-panel playback automation (wait for
    // results → click first video → play → unmute → verify) via invoke IPC.
    useEffect(() => {
        if (openUrl && openUrl.url) {
            setInputUrl(openUrl.url);
            const ytMatch = /youtube\.com\/results\?search_query=([^&]+)/i.exec(openUrl.url);
            if (ytMatch && ipcRenderer.invoke) {
                const query = decodeURIComponent(ytMatch[1].replace(/\+/g, ' '));
                ipcRenderer.invoke('browser-youtube-play', { tabId: activeTabId, query })
                    .then(res => { console.log('[YT PLAY]', JSON.stringify(res)); })
                    .catch(err => {
                        console.warn('[YT PLAY] failed, plain load:', err);
                        ipcRenderer.send('browser-load', { tabId: activeTabId, url: openUrl.url });
                    });
            } else {
                ipcRenderer.send('browser-load', { tabId: activeTabId, url: openUrl.url });
            }
            setTimeout(updateBounds, 80);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [openUrl?.ts]);

    // Initialize tabs on mount
    useEffect(() => {
        tabs.forEach(t => {
            ipcRenderer.send('browser-create-tab', { tabId: t.id, url: t.url });
        });
        ipcRenderer.send('browser-switch-tab', { tabId: activeTabId });
        
        // Listeners for WebContents events from main process
        const onLoading = (e, { tabId, loading }) => {
            setTabs(prev => prev.map(t => t.id === tabId ? { ...t, loading } : t));
        };
        const onTitle = (e, { tabId, title }) => {
            setTabs(prev => prev.map(t => t.id === tabId ? { ...t, title } : t));
        };
        const onFavicon = (e, { tabId, favicon }) => {
            setTabs(prev => prev.map(t => t.id === tabId ? { ...t, favicon } : t));
        };
        const onNavigate = (e, { tabId, url }) => {
            setTabs(prev => prev.map(t => t.id === tabId ? { ...t, url } : t));
            if (tabId === activeTabId) {
                setInputUrl(url);
            }
        };
        const onNewTab = (e, { url }) => {
            handleAddTab(url);
        };

        // Stale-view / crash recovery: recreate the BrowserView for a tab whose
        // renderer died or went missing, then reload its last URL.
        const onCrashed = (e, { tabId }) => {
            const tab = tabsRef.current.find(t => t.id === tabId);
            const url = tab ? tab.url : 'https://www.google.com';
            ipcRenderer.send('browser-create-tab', { tabId, url });
            if (tabId === activeTabIdRef.current) {
                ipcRenderer.send('browser-switch-tab', { tabId });
            }
        };
        const onStale = (e, { tabId, url }) => {
            ipcRenderer.send('browser-create-tab', { tabId, url });
            ipcRenderer.send('browser-switch-tab', { tabId });
            ipcRenderer.send('browser-load', { tabId, url });
        };

        // Download event listeners
        const onDownloadStart = (e, item) => {
            setDownloads(prev => [...prev, { ...item, progress: 0, state: 'progressing' }]);
            setShowDownloads(true);
        };
        const onDownloadUpdate = (e, item) => {
            setDownloads(prev => prev.map(d => d.id === item.id ? { 
                ...d, 
                state: item.state, 
                progress: item.receivedBytes ? Math.round((item.receivedBytes / d.totalBytes) * 100) : d.progress 
            } : d));
        };
        const onDownloadDone = (e, item) => {
            setDownloads(prev => prev.map(d => d.id === item.id ? { ...d, state: item.state, progress: 100 } : d));
        };

        ipcRenderer.on('browser-event-loading', onLoading);
        ipcRenderer.on('browser-event-title', onTitle);
        ipcRenderer.on('browser-event-favicon', onFavicon);
        ipcRenderer.on('browser-event-navigate', onNavigate);
        ipcRenderer.on('browser-event-new-tab', onNewTab);
        ipcRenderer.on('browser-event-crashed', onCrashed);
        ipcRenderer.on('browser-event-stale', onStale);

        ipcRenderer.on('download-event-start', onDownloadStart);
        ipcRenderer.on('download-event-update', onDownloadUpdate);
        ipcRenderer.on('download-event-done', onDownloadDone);

        // ResizeObserver to track accurate container boundaries in real time
        let observer;
        if (placeholderRef.current) {
            observer = new ResizeObserver(() => {
                updateBounds();
            });
            observer.observe(placeholderRef.current);
        }

        window.addEventListener('resize', updateBounds);
        setTimeout(updateBounds, 100);
        setTimeout(updateBounds, 300);
        setTimeout(updateBounds, 600);

        return () => {
            ipcRenderer.off('browser-event-loading', onLoading);
            ipcRenderer.off('browser-event-title', onTitle);
            ipcRenderer.off('browser-event-favicon', onFavicon);
            ipcRenderer.off('browser-event-navigate', onNavigate);
            ipcRenderer.off('browser-event-new-tab', onNewTab);
            ipcRenderer.off('browser-event-crashed', onCrashed);
            ipcRenderer.off('browser-event-stale', onStale);

            ipcRenderer.off('download-event-start', onDownloadStart);
            ipcRenderer.off('download-event-update', onDownloadUpdate);
            ipcRenderer.off('download-event-done', onDownloadDone);

            window.removeEventListener('resize', updateBounds);
            if (observer) {
                observer.disconnect();
            }
            // Cancel any pending coalesced bounds send + reset cache so a later
            // re-open re-sends fresh geometry.
            if (boundsRafRef.current) {
                cancelAnimationFrame(boundsRafRef.current);
                boundsRafRef.current = 0;
            }
            lastBoundsRef.current = null;
            // Hide browser views when exiting
            ipcRenderer.send('browser-set-bounds', { visible: false });
        };
    }, []);

    // Helper to calculate and sync target WebContents coordinates.
    // Coalesced via requestAnimationFrame + dedup so a burst of callers
    // (mount timers, ResizeObserver, tab switch) results in ONE IPC send,
    // and repeated identical bounds send nothing (no flicker).
    const updateBounds = () => {
        if (boundsRafRef.current) return; // already scheduled this frame
        boundsRafRef.current = requestAnimationFrame(() => {
            boundsRafRef.current = 0;
            if (!placeholderRef.current) return;
            const rect = placeholderRef.current.getBoundingClientRect();
            const next = {
                x: Math.round(rect.left),
                y: Math.round(rect.top),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                visible: true,
            };
            const prev = lastBoundsRef.current;
            if (prev && prev.x === next.x && prev.y === next.y &&
                prev.width === next.width && prev.height === next.height) {
                return; // geometry unchanged — skip redundant reposition
            }
            lastBoundsRef.current = next;
            ipcRenderer.send('browser-set-bounds', next);
        });
    };

    // Navigation triggers
    const handleUrlSubmit = (e) => {
        if (e.key === 'Enter' && inputUrl.trim()) {
            ipcRenderer.send('browser-load', { tabId: activeTabId, url: inputUrl });
        }
    };

    const handleGoBack = () => ipcRenderer.send('browser-go-back', { tabId: activeTabId });
    const handleGoForward = () => ipcRenderer.send('browser-go-forward', { tabId: activeTabId });
    const handleReload = () => ipcRenderer.send('browser-reload', { tabId: activeTabId });
    const handleToggleDevTools = () => ipcRenderer.send('browser-devtools', { tabId: activeTabId });

    const handleAddTab = (url = 'https://www.google.com') => {
        const newTabId = 'tab-' + Date.now();
        const newTab = { id: newTabId, title: 'New Tab', url, loading: false, favicon: null };
        setTabs(prev => [...prev, newTab]);
        ipcRenderer.send('browser-create-tab', { tabId: newTabId, url });
        setActiveTabId(newTabId);
    };

    const handleCloseTab = (tabId, e) => {
        e.stopPropagation();
        if (tabs.length === 1) return; // Keep at least one tab

        const index = tabs.findIndex(t => t.id === tabId);
        const filtered = tabs.filter(t => t.id !== tabId);
        setTabs(filtered);

        ipcRenderer.send('browser-close-tab', { tabId });

        if (activeTabId === tabId) {
            const nextActiveTab = filtered[index - 1] || filtered[0];
            setActiveTabId(nextActiveTab.id);
        }
    };

    const handleToggleBookmark = () => {
        const activeTab = tabs.find(t => t.id === activeTabId);
        if (!activeTab) return;

        const isBookmarked = bookmarks.some(b => b.url === activeTab.url);
        if (isBookmarked) {
            setBookmarks(prev => prev.filter(b => b.url !== activeTab.url));
        } else {
            setBookmarks(prev => [...prev, { title: activeTab.title, url: activeTab.url }]);
        }
    };

    const handleLoadBookmark = (url) => {
        setInputUrl(url);
        ipcRenderer.send('browser-load', { tabId: activeTabId, url });
    };

    // Prompt injector shortcuts
    const triggerPromptShortcut = (text) => {
        setInputValue(text);
        socket.emit('user_input', { text });
        if (messagesEndRef && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    };

    const activeTab = tabs.find(t => t.id === activeTabId);
    const isBookmarked = activeTab && bookmarks.some(b => b.url === activeTab.url);

    return (
        <div className="flex-1 flex gap-6 h-full w-full overflow-hidden min-h-0 pb-2">
            {/* ============ LEFT COLUMN: BROWSER VIEW WORKSPACE ============ */}
            <div className="flex-[1.6] min-w-0 flex flex-col glass-level-2 rounded-3xl border border-white/5 overflow-hidden relative min-h-0">
                {/* 1. Address Bar & Navigation Buttons */}
                <div className="flex flex-col border-b border-white/5 bg-black/40 backdrop-blur-md px-4 py-2.5 space-y-1.5 shrink-0">
                    <div className="flex items-center gap-3">
                        {/* Navigation controls */}
                        <div className="flex items-center gap-1.5">
                            <button onClick={handleGoBack} className="p-1.5 hover:bg-white/5 rounded-lg text-on-surface-variant hover:text-primary transition-colors"><ChevronLeft size={16} /></button>
                            <button onClick={handleGoForward} className="p-1.5 hover:bg-white/5 rounded-lg text-on-surface-variant hover:text-primary transition-colors"><ChevronRight size={16} /></button>
                            <button onClick={handleReload} className="p-1.5 hover:bg-white/5 rounded-lg text-on-surface-variant hover:text-primary transition-colors"><RotateCw size={14} /></button>
                        </div>

                        {/* URL box */}
                        <div className="flex-1 flex items-center bg-white/5 border border-white/10 rounded-xl px-4 py-1.5 gap-2 relative">
                            <Shield size={12} className="text-primary/60" />
                            <input
                                type="text"
                                value={inputUrl}
                                onChange={(e) => setInputUrl(e.target.value)}
                                onKeyDown={handleUrlSubmit}
                                className="flex-1 bg-transparent border-0 outline-none text-white text-xs font-mono select-all focus:ring-0 placeholder-on-surface-variant/30"
                            />
                            <button onClick={handleToggleBookmark} className={`p-1 rounded hover:bg-white/5 transition-colors ${isBookmarked ? 'text-primary' : 'text-on-surface-variant'}`} title="Bookmark page">
                                <Bookmark size={14} className={isBookmarked ? 'fill-current' : ''} />
                            </button>
                        </div>

                        {/* Actions drawer */}
                        <div className="flex items-center gap-1.5">
                            <button onClick={() => setShowDownloads(!showDownloads)} className={`p-1.5 rounded-lg hover:bg-white/5 transition-all ${showDownloads ? 'bg-primary-container/20 text-primary' : 'text-on-surface-variant'}`} title="Downloads"><Download size={15} /></button>
                            <button onClick={handleToggleDevTools} className="p-1.5 rounded-lg hover:bg-white/5 text-on-surface-variant hover:text-primary transition-colors" title="Developer tools"><Terminal size={15} /></button>
                            <button onClick={() => handleAddTab()} className="p-1.5 bg-primary-container/20 border border-primary-container/30 text-primary rounded-lg hover:scale-105 transition-transform"><Plus size={15} /></button>
                        </div>
                    </div>

                    {/* Bookmarks Quick Bar */}
                    {bookmarks.length > 0 && (
                        <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide py-1">
                            {bookmarks.map((b, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleLoadBookmark(b.url)}
                                    className="flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/5 hover:border-primary-container/40 rounded-full text-[10px] text-on-surface-variant hover:text-primary font-mono transition-all whitespace-nowrap"
                                >
                                    <Bookmark size={8} className="fill-current text-primary" />
                                    <span>{b.title}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Tabs Bar */}
                <div className="flex items-center gap-2 bg-black/60 border-b border-white/5 px-4 py-1.5 overflow-x-auto scrollbar-hide shrink-0">
                    {tabs.map((tab) => {
                        const isActive = tab.id === activeTabId;
                        return (
                            <div
                                key={tab.id}
                                onClick={() => setActiveTabId(tab.id)}
                                className={`group flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-mono transition-all duration-300 cursor-pointer max-w-[160px] truncate border select-none ${
                                    isActive
                                        ? 'bg-primary-container/10 border-primary-container/40 text-primary shadow-[0_0_12px_rgba(0,212,255,0.15)] font-semibold'
                                        : 'bg-white/5 border-transparent text-on-surface-variant hover:bg-white/10 hover:text-white'
                                }`}
                            >
                                {tab.favicon ? (
                                    <img src={tab.favicon} alt="" className="w-3.5 h-3.5 object-contain" />
                                ) : (
                                    <div className={`w-2 h-2 rounded-full ${tab.loading ? 'bg-primary animate-pulse' : 'bg-on-surface-variant/30'}`} />
                                )}
                                <span className="truncate flex-1 text-[11px]">{tab.title}</span>
                                {tabs.length > 1 && (
                                    <button
                                        onClick={(e) => handleCloseTab(tab.id, e)}
                                        className="p-0.5 rounded-full hover:bg-white/20 text-on-surface-variant group-hover:opacity-100 opacity-0 transition-opacity ml-1.5"
                                    >
                                        <X size={10} />
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* 2. Target WebContents View Placeholder */}
                <div ref={placeholderRef} className="flex-1 w-full bg-[#030405] relative min-h-0" />

                {/* 3. Download Progress Drawer overlay */}
                {showDownloads && downloads.length > 0 && (
                    <div className="absolute right-4 bottom-4 w-72 glass-panel border border-white/10 rounded-2xl shadow-2xl p-4 flex flex-col space-y-3 z-50 animate-fade-in max-h-60 overflow-y-auto scrollbar-hide">
                        <div className="flex justify-between items-center border-b border-white/5 pb-2 shrink-0">
                            <span className="font-mono text-xs font-bold text-primary tracking-widest">DOWNLOADS</span>
                            <button onClick={() => setShowDownloads(false)} className="text-on-surface-variant hover:text-white text-xs">✕</button>
                        </div>
                        <div className="flex flex-col gap-3 overflow-y-auto">
                            {downloads.map((d) => (
                                <div key={d.id} className="flex flex-col gap-1.5 p-2 bg-white/5 border border-white/5 rounded-lg text-[10px]">
                                    <div className="flex justify-between font-mono font-medium text-white truncate">
                                        <span className="truncate">{d.name}</span>
                                        <span>{d.progress}%</span>
                                    </div>
                                    <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
                                        <div className="bg-primary h-full rounded-full transition-all duration-300" style={{ width: `${d.progress}%` }} />
                                    </div>
                                    <div className="flex justify-between text-[9px] text-on-surface-variant opacity-60 font-mono">
                                        <span>{d.state}</span>
                                        <span>{Math.round(d.totalBytes / 1024 / 1024 * 10) / 10} MB</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* ============ RIGHT COLUMN: INTEGRATED LUMINA ASSISTANT SIDE PANEL ============ */}
            <div className="flex-1 min-w-[320px] max-w-[520px] flex flex-col justify-between shrink-0 h-full border border-white/5 rounded-3xl bg-black/40 backdrop-blur-2xl p-5 relative overflow-hidden min-h-0">
                {/* Backlighting */}
                <div className="absolute top-[-10%] right-[-10%] w-48 h-48 rounded-full bg-primary/5 blur-[50px] pointer-events-none" />

                {/* 1. Header and Quick action prompts */}
                <div className="flex flex-col space-y-3 shrink-0">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <Sparkles size={14} className="text-primary" />
                            <span className="font-sora text-sm font-semibold text-white tracking-wide">Assistant</span>
                        </div>
                        <span className="font-mono text-[10px] text-primary/60 uppercase">TIMELINE</span>
                    </div>

                    {/* AI Document / Page query prompt injection shortcuts */}
                    <div className="grid grid-cols-2 gap-2">
                        <button
                            onClick={() => triggerPromptShortcut("Lumina, summarize this page.")}
                            className="glass-level-2 border border-white/5 rounded-xl px-3 py-1.5 text-[10px] text-left text-on-surface-variant hover:text-primary hover:border-primary-container/40 transition-all cursor-pointer font-mono"
                        >
                            ⚡ Summarize
                        </button>
                        <button
                            onClick={() => triggerPromptShortcut("Lumina, explain what this page says.")}
                            className="glass-level-2 border border-white/5 rounded-xl px-3 py-1.5 text-[10px] text-left text-on-surface-variant hover:text-primary hover:border-primary-container/40 transition-all cursor-pointer font-mono"
                        >
                            💡 Explain
                        </button>
                        <button
                            onClick={() => triggerPromptShortcut("Lumina, save this page details to my memory.")}
                            className="glass-level-2 border border-white/5 rounded-xl px-3 py-1.5 text-[10px] text-left text-on-surface-variant hover:text-primary hover:border-primary-container/40 transition-all cursor-pointer font-mono"
                        >
                            🧠 Save Fact
                        </button>
                        <button
                            onClick={() => triggerPromptShortcut("Lumina, translate this page.")}
                            className="glass-level-2 border border-white/5 rounded-xl px-3 py-1.5 text-[10px] text-left text-on-surface-variant hover:text-primary hover:border-primary-container/40 transition-all cursor-pointer font-mono"
                        >
                            🌐 Translate
                        </button>
                    </div>
                </div>

                {/* 2. Centered visualizer orb */}
                <div className="flex items-center justify-center py-2 relative shrink-0">
                    <Visualizer
                        audioData={aiAudioData}
                        isListening={isConnected && !isMuted}
                        intensity={audioAmp}
                        width={140}
                        height={140}
                    />
                </div>

                {/* 3. Timeline / Recent transcript window */}
                <div className="flex-1 overflow-y-auto scrollbar-hide space-y-2 py-2 border-t border-white/5 mt-1 mask-image-gradient min-h-0">
                    {messages.slice(-4).map((msg, i) => (
                        <div key={i} className={`p-2.5 rounded-xl border-l-2 relative overflow-hidden transition-all duration-300 ${
                            msg.sender === 'You' ? 'bg-white/5 border-l-primary/70' : 'bg-primary-container/5 border-l-secondary-fixed/70'
                        }`}>
                            <div className="flex justify-between items-center text-[9px] text-on-surface-variant opacity-60 font-mono">
                                <span>{msg.sender}</span>
                                <span>{msg.time}</span>
                            </div>
                            <p className="font-manrope text-[11px] text-on-surface mt-0.5 leading-relaxed">
                                {msg.text}
                            </p>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* 4. Side Quest Chat input Row with integrated Mic button */}
                <div className="w-full flex items-center bg-white/5 border border-white/10 rounded-full px-3 py-1.5 backdrop-blur-md shadow-xl gap-2 mt-3 shrink-0">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleSendKey}
                        placeholder="Ask Luna about this page..."
                        className="flex-1 bg-transparent border-0 outline-none text-white text-[11px] placeholder-on-surface-variant/40 focus:ring-0 py-1"
                    />

                    {/* Integrated Mic Button inside chat row */}
                    <button
                        onClick={toggleMute}
                        disabled={!isConnected}
                        className={`p-1.5 rounded-full border transition-all duration-300 ${
                            !isConnected
                                ? 'border-transparent text-on-surface-variant/20'
                                : isMuted
                                    ? 'border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 shadow-[0_0_8px_rgba(239,68,68,0.15)]'
                                    : 'border-primary-container/30 bg-primary-container/10 text-primary hover:bg-primary-container/20 shadow-[0_0_8px_rgba(6,182,212,0.15)]'
                        }`}
                        title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
                    >
                        {isMuted ? <MicOff size={12} /> : <Mic size={12} />}
                    </button>

                    {/* Send Button */}
                    <button
                        onClick={handleSendClick}
                        disabled={!inputValue.trim()}
                        className={`p-1.5 rounded-full border transition-all duration-300 ${
                            inputValue.trim()
                                ? 'border-primary-container/40 bg-primary-container/20 text-primary hover:scale-105 shadow-[0_0_8px_rgba(6,182,212,0.15)]'
                                : 'border-transparent text-on-surface-variant/20'
                        }`}
                    >
                        <Send size={12} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default BrowserWorkspacePanel;
