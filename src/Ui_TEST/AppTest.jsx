import React, { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import { Mic, MicOff, Settings, X, Minus, Power, Send, PanelLeftOpen, PanelLeftClose, Clock, ChevronRight } from 'lucide-react';

// Reuse production components (no duplication)
import Visualizer from '../components/Visualizer';
import TopAudioBar from '../components/TopAudioBar';
// SystemSettingsPanel replaces old SettingsWindow — rendered as a panel, not overlay
import ConfirmationPopup from '../components/ConfirmationPopup';
import BrowserWindow from '../components/BrowserWindow';
import CadWindow from '../components/CadWindow';

// New Ui_TEST panels
import Sidebar from './components/Sidebar';
import KnowledgeArchivePanel from './panels/KnowledgeArchivePanel';
import EventsPanel from './panels/EventsPanel';
import QuestsPanel from './panels/QuestsPanel';
import SystemSettingsPanel from './panels/SystemSettingsPanel';

const socket = io('http://localhost:8000');
const { ipcRenderer } = window.require('electron');

function AppTest() {
    // ========================================
    // STATE — mirrors production App.jsx exactly for backend compat
    // ========================================
    const [status, setStatus] = useState('Disconnected');
    const [socketConnected, setSocketConnected] = useState(socket.connected);
    const [connectionStatus, setConnectionStatus] = useState('connected');
    const [modelStatus, setModelStatus] = useState('disconnected');
    const [isConnected, setIsConnected] = useState(true);
    const [isMuted, setIsMuted] = useState(true);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [currentProject, setCurrentProject] = useState('default');
    const [currentTime, setCurrentTime] = useState(new Date());
    const [confirmationRequest, setConfirmationRequest] = useState(null);
    // showSettings removed — settings is now a panel, not an overlay

    // Audio data
    const [aiAudioData, setAiAudioData] = useState(new Array(64).fill(0));
    const [micAudioData, setMicAudioData] = useState(new Array(32).fill(0));

    // Devices
    const [micDevices, setMicDevices] = useState([]);
    const [speakerDevices, setSpeakerDevices] = useState([]);
    const [webcamDevices, setWebcamDevices] = useState([]);
    const [selectedMicId, setSelectedMicId] = useState(() => localStorage.getItem('selectedMicId') || '');
    const [selectedSpeakerId, setSelectedSpeakerId] = useState(() => localStorage.getItem('selectedSpeakerId') || '');
    const [selectedWebcamId, setSelectedWebcamId] = useState(() => localStorage.getItem('selectedWebcamId') || '');

    // Camera flip (for SettingsWindow compat)
    const [isCameraFlipped, setIsCameraFlipped] = useState(false);
    const [cursorSensitivity, setCursorSensitivity] = useState(2.0);

    // Browser / CAD overlays
    const [cadData, setCadData] = useState(null);
    const [cadThoughts, setCadThoughts] = useState('');
    const [cadRetryInfo, setCadRetryInfo] = useState({ attempt: 1, maxAttempts: 3, error: null });
    const [browserData, setBrowserData] = useState({ image: null, logs: [] });
    const [showCadWindow, setShowCadWindow] = useState(false);
    const [showBrowserWindow, setShowBrowserWindow] = useState(false);

    // NEW: Sidebar & Panel switching
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [activePanel, setActivePanel] = useState('home'); // 'home' | 'archive' | 'events' | 'quests' | 'settings'

    // Alarm overlay
    const [alarmEvent, setAlarmEvent] = useState(null);

    // Refs
    const messagesEndRef = useRef(null);
    const hasAutoConnectedRef = useRef(false);
    const lifecycleSeenRef = useRef(new Set());

    // Mic visualizer refs
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const sourceRef = useRef(null);
    const animationFrameRef = useRef(null);

    // ========================================
    // EFFECTS — same socket wiring as production
    // ========================================
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-connect
    useEffect(() => {
        if (isConnected && socketConnected && micDevices.length > 0 && !hasAutoConnectedRef.current) {
            hasAutoConnectedRef.current = true;
            socket.emit('discover_kasa');
            socket.emit('discover_printers');
            const timer = setTimeout(() => {
                const index = micDevices.findIndex(d => d.deviceId === selectedMicId);
                const queryDevice = micDevices.find(d => d.deviceId === selectedMicId);
                const deviceName = queryDevice ? queryDevice.label : null;
                setStatus('Connecting...');
                socket.emit('start_audio', {
                    device_index: index >= 0 ? index : null,
                    device_name: deviceName,
                    muted: isMuted
                });
            }, 500);
            return () => clearTimeout(timer);
        }
    }, [isConnected, socketConnected, micDevices, selectedMicId]);

    // Socket events
    useEffect(() => {
        socket.on('hb_ping', () => socket.emit('hb_pong'));
        socket.on('connection_status', (data) => setConnectionStatus(data.status));
        socket.on('model_status', (data) => setModelStatus(data.status));

        socket.on('connect', () => {
            setStatus('Connected');
            setSocketConnected(true);
            setConnectionStatus('connected');
            socket.emit('get_settings');
        });
        socket.on('disconnect', () => {
            setStatus('Disconnected');
            setSocketConnected(false);
            setConnectionStatus('offline');
        });
        socket.on('status', (data) => {
            addMessage('System', data.msg);
            if (data.msg === 'Lumina Started') setStatus('Model Connected');
            else if (data.msg === 'Lumina Stopped') setStatus('Connected');
        });
        socket.on('audio_data', (data) => setAiAudioData(data.data));

        socket.on('settings', (settings) => {
            if (typeof settings.camera_flipped !== 'undefined') setIsCameraFlipped(settings.camera_flipped);
        });
        socket.on('error', (data) => addMessage('System', `Error: ${data.msg}`));

        socket.on('cad_data', (data) => {
            setCadData(data);
            setCadThoughts('');
            setShowCadWindow(true);
        });
        socket.on('cad_status', (data) => {
            if (data.attempt) setCadRetryInfo({ attempt: data.attempt, maxAttempts: data.max_attempts || 3, error: data.error });
            if (data.status === 'generating' || data.status === 'retrying') {
                setCadData({ format: 'loading' });
                setShowCadWindow(true);
                if (data.status === 'generating' && data.attempt === 1) setCadThoughts('');
            }
        });
        socket.on('cad_thought', (data) => setCadThoughts(prev => prev + data.text));

        socket.on('browser_frame', (data) => {
            setBrowserData(prev => ({ image: data.image, logs: [...prev.logs, data.log].filter(l => l).slice(-50) }));
            setShowBrowserWindow(true);
        });

        socket.on('transcription', (data) => {
            setMessages(prev => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg && lastMsg.sender === data.sender) {
                    return [...prev.slice(0, -1), { ...lastMsg, text: lastMsg.text + data.text }];
                }
                return [...prev, { sender: data.sender, text: data.text, time: new Date().toLocaleTimeString() }];
            });
        });

        socket.on('chat_message', (data) => {
            setMessages(prev => [...prev, { sender: data.sender || 'System', text: data.text, time: new Date().toLocaleTimeString() }]);
        });

        socket.on('tool_confirmation_request', (data) => setConfirmationRequest(data));
        socket.on('project_update', (data) => {
            setCurrentProject(data.project);
            addMessage('System', `Switched to project: ${data.project}`);
        });

        socket.on('reminder_alarm', (evt) => {
            setAlarmEvent(evt);
            // Play alarm sound
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = 880;
                osc.type = 'sine';
                gain.gain.value = 0.3;
                osc.start();
                setTimeout(() => { gain.gain.value = 0; }, 200);
                setTimeout(() => { gain.gain.value = 0.3; }, 400);
                setTimeout(() => { gain.gain.value = 0; }, 600);
                setTimeout(() => { gain.gain.value = 0.3; }, 800);
                setTimeout(() => { gain.gain.value = 0; osc.stop(); ctx.close(); }, 1000);
            } catch (e) { /* audio not available */ }
            // Auto-dismiss after 15 seconds (also triggers follow-up)
            setTimeout(() => {
                setAlarmEvent(prev => {
                    if (prev && prev.id === evt.id) {
                        socket.emit('reminder_alarm_dismissed', {
                            event_id: evt.id,
                            title: evt.title,
                            dismissed_at_iso: new Date().toISOString(),
                        });
                        return null;
                    }
                    return prev;
                });
            }, 15000);
        });

        // Panel navigation via voice/typed command
        socket.on('navigate_panel', (data) => {
            const panel = data.panel || 'home';
            setActivePanel(panel);
            if (panel !== 'home') setSidebarOpen(true);
            console.log(`[NAV] source=${data.source || 'server'} panel=${panel} view=${data.view || 'all'}`);
        });

        // Device enumeration
        navigator.mediaDevices.enumerateDevices().then(devs => {
            setMicDevices(devs.filter(d => d.kind === 'audioinput'));
            setSpeakerDevices(devs.filter(d => d.kind === 'audiooutput'));
            setWebcamDevices(devs.filter(d => d.kind === 'videoinput'));

            const savedMic = localStorage.getItem('selectedMicId');
            const audioInputs = devs.filter(d => d.kind === 'audioinput');
            if (savedMic && audioInputs.some(d => d.deviceId === savedMic)) setSelectedMicId(savedMic);
            else if (audioInputs.length > 0) setSelectedMicId(audioInputs[0].deviceId);
        });

        return () => {
            socket.off('connect'); socket.off('disconnect'); socket.off('status');
            socket.off('audio_data'); socket.off('cad_data'); socket.off('cad_thought');
            socket.off('cad_status'); socket.off('browser_frame'); socket.off('transcription');
            socket.off('tool_confirmation_request'); socket.off('error');
            socket.off('reminder_alarm');
            socket.off('navigate_panel');
            stopMicVisualizer();
        };
    }, []);

    // Memory lifecycle (debug only, same as production)
    useEffect(() => {
        const handler = (data) => {
            const key = `${data.event}:${data.memory_id ?? data.id ?? 'na'}:${data.ts ?? 'na'}`;
            if (lifecycleSeenRef.current.has(key)) return;
            lifecycleSeenRef.current.add(key);
            if (lifecycleSeenRef.current.size > 300) { lifecycleSeenRef.current.clear(); lifecycleSeenRef.current.add(key); }
        };
        socket.on('memory_lifecycle_event', handler);
        return () => socket.off('memory_lifecycle_event', handler);
    }, []);

    // Initial settings fetch
    useEffect(() => { if (socket.connected) { setStatus('Connected'); socket.emit('get_settings'); } }, []);

    // Persist device selections
    useEffect(() => { if (selectedMicId) localStorage.setItem('selectedMicId', selectedMicId); }, [selectedMicId]);
    useEffect(() => { if (selectedSpeakerId) localStorage.setItem('selectedSpeakerId', selectedSpeakerId); }, [selectedSpeakerId]);

    // Mic visualizer
    useEffect(() => { if (selectedMicId) startMicVisualizer(selectedMicId); }, [selectedMicId]);

    // ========================================
    // HANDLERS — identical to production
    // ========================================
    const addMessage = (sender, text) => {
        setMessages(prev => [...prev, { sender, text, time: new Date().toLocaleTimeString() }]);
    };

    const togglePower = () => {
        if (isConnected) {
            socket.emit('stop_audio');
            setIsConnected(false);
            setIsMuted(false);
        } else {
            const index = micDevices.findIndex(d => d.deviceId === selectedMicId);
            socket.emit('start_audio', { device_index: index >= 0 ? index : null });
            setIsConnected(true);
            setIsMuted(false);
        }
    };

    const toggleMute = () => {
        if (!isConnected) return;
        if (isMuted) { socket.emit('resume_audio'); setIsMuted(false); }
        else { socket.emit('pause_audio'); setIsMuted(true); }
    };

    const handleSendClick = () => {
        if (inputValue.trim()) {
            socket.emit('user_input', { text: inputValue });
            addMessage('You', inputValue);
            setInputValue('');
        }
    };

    const handleSendKey = (e) => {
        if (e.key === 'Enter' && inputValue.trim()) {
            socket.emit('user_input', { text: inputValue });
            addMessage('You', inputValue);
            setInputValue('');
        }
    };

    const handleMinimize = () => ipcRenderer.send('window-minimize');
    const handleMaximize = () => ipcRenderer.send('window-maximize');
    const handleCloseRequest = () => {
        const closeWindow = () => ipcRenderer.send('window-close');
        if (socket.connected) {
            socket.emit('shutdown', {}, () => closeWindow());
            setTimeout(closeWindow, 500);
        } else closeWindow();
    };

    const handleConfirmTool = () => {
        if (confirmationRequest) { socket.emit('confirm_tool', { id: confirmationRequest.id, confirmed: true }); setConfirmationRequest(null); }
    };
    const handleDenyTool = () => {
        if (confirmationRequest) { socket.emit('confirm_tool', { id: confirmationRequest.id, confirmed: false }); setConfirmationRequest(null); }
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            const textContent = event.target.result;
            if (typeof textContent === 'string' && textContent.length > 0) {
                socket.emit('upload_memory', { memory: textContent });
                addMessage('System', 'Uploading memory...');
            }
        };
        reader.readAsText(file);
    };

    const startMicVisualizer = async (deviceId) => {
        stopMicVisualizer();
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { deviceId: { exact: deviceId } } });
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
            analyserRef.current = audioContextRef.current.createAnalyser();
            analyserRef.current.fftSize = 64;
            sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);
            sourceRef.current.connect(analyserRef.current);
            const update = () => {
                if (!analyserRef.current) return;
                const arr = new Uint8Array(analyserRef.current.frequencyBinCount);
                analyserRef.current.getByteFrequencyData(arr);
                setMicAudioData(Array.from(arr));
                animationFrameRef.current = requestAnimationFrame(update);
            };
            update();
        } catch (err) { console.error('Mic visualizer error:', err); }
    };

    const stopMicVisualizer = () => {
        if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
        if (sourceRef.current) sourceRef.current.disconnect();
        if (audioContextRef.current) audioContextRef.current.close();
    };

    // Panel navigation
    const navigateToPanel = (panel) => {
        setActivePanel(panel);
        if (window.innerWidth < 1024) setSidebarOpen(false); // auto-close on small screens
    };

    const audioAmp = aiAudioData.reduce((a, b) => a + b, 0) / aiAudioData.length / 255;

    // ========================================
    // RENDER
    // ========================================
    return (
        <div className="h-screen w-screen bg-black text-cyan-100 font-mono overflow-hidden flex flex-col relative selection:bg-cyan-900 selection:text-white">
            {/* Background layers */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-gray-900 via-black to-black z-0 pointer-events-none" style={{ opacity: 0.6 }} />
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 z-0 pointer-events-none mix-blend-overlay" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-900/10 rounded-full blur-[120px] pointer-events-none" />

            {/* ============ TOP BAR ============ */}
            <div className="z-50 flex items-center justify-between p-2 border-b border-cyan-500/20 bg-black/60 backdrop-blur-md select-none shrink-0" style={{ WebkitAppRegion: 'drag' }}>
                <div className="flex items-center gap-3 pl-2" style={{ WebkitAppRegion: 'no-drag' }}>
                    {/* Sidebar Toggle */}
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="p-1.5 rounded-md border border-cyan-800/40 text-cyan-500 hover:bg-cyan-900/30 hover:border-cyan-500/50 transition-all duration-200"
                        title="Toggle sidebar"
                    >
                        {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
                    </button>

                    <h1 className="text-xl font-bold tracking-[0.2em] text-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                        LUMINA
                    </h1>
                    <div className="text-[10px] text-cyan-700 border border-cyan-900 px-1 rounded">V2.0.0</div>

                    {/* Connection Status */}
                    <div className={`text-[10px] px-2 py-0.5 rounded border flex items-center gap-1 ${
                        connectionStatus === 'connected'
                            ? 'text-green-400 border-green-500/30 bg-green-500/10'
                            : connectionStatus === 'reconnecting'
                            ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10 animate-pulse'
                            : 'text-red-400 border-red-500/30 bg-red-500/10'
                    }`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${
                            connectionStatus === 'connected' ? 'bg-green-400' :
                            connectionStatus === 'reconnecting' ? 'bg-yellow-400' : 'bg-red-400'
                        }`} />
                        <span>{connectionStatus === 'connected' ? 'Connected' : connectionStatus === 'reconnecting' ? 'Reconnecting' : 'Offline'}</span>
                    </div>

                    {/* Power Toggle */}
                    <button
                        onClick={togglePower}
                        className={`p-1.5 rounded-full border transition-all duration-300 ${isConnected
                            ? 'border-green-500/50 text-green-500 hover:bg-green-500/10 shadow-[0_0_8px_rgba(34,197,94,0.2)]'
                            : 'border-gray-600/50 text-gray-500 hover:bg-gray-600/10'
                        }`}
                    >
                        <Power size={14} />
                    </button>
                </div>

                {/* Center: Mic Visualizer */}
                <div className="flex-1 flex justify-center mx-4">
                    <TopAudioBar audioData={micAudioData} />
                </div>

                {/* Right side */}
                <div className="flex items-center gap-2 pr-2" style={{ WebkitAppRegion: 'no-drag' }}>
                    <div className="flex items-center gap-1.5 text-[11px] text-cyan-300/70 font-mono px-2">
                        <Clock size={12} className="text-cyan-500/50" />
                        <span>{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>

                    {/* Settings Icon (top-right) — opens settings panel */}
                    <button
                        onClick={() => navigateToPanel(activePanel === 'settings' ? 'home' : 'settings')}
                        className={`p-1.5 rounded-md border transition-all duration-200 ${activePanel === 'settings'
                            ? 'border-cyan-400/60 text-cyan-400 bg-cyan-900/20 shadow-[0_0_8px_rgba(34,211,238,0.2)]'
                            : 'border-cyan-800/40 text-cyan-600 hover:border-cyan-500/50 hover:text-cyan-400'
                        }`}
                        title="Settings"
                    >
                        <Settings size={16} />
                    </button>

                    <button onClick={handleMinimize} className="p-1 hover:bg-cyan-900/50 rounded text-cyan-500 transition-colors"><Minus size={18} /></button>
                    <button onClick={handleMaximize} className="p-1 hover:bg-cyan-900/50 rounded text-cyan-500 transition-colors"><div className="w-[14px] h-[14px] border-2 border-current rounded-[2px]" /></button>
                    <button onClick={handleCloseRequest} className="p-1 hover:bg-red-900/50 rounded text-red-500 transition-colors"><X size={18} /></button>
                </div>
            </div>

            {/* ============ MAIN BODY (sidebar + content) ============ */}
            <div className="flex-1 flex overflow-hidden relative z-10">
                {/* Sidebar */}
                <Sidebar
                    isOpen={sidebarOpen}
                    activePanel={activePanel}
                    onNavigate={navigateToPanel}
                />

                {/* Main Content Area */}
                <div className="flex-1 flex flex-col min-w-0 relative">
                    {/* Panel Content OR Home (Visualizer + Chat) */}
                    {activePanel === 'home' ? (
                        <>
                            {/* Floating Project Label */}
                            <div className="absolute top-2 left-1/2 -translate-x-1/2 text-cyan-500 text-xs font-mono tracking-widest pointer-events-none z-40 bg-black/50 px-2 py-1 rounded backdrop-blur-sm border border-cyan-500/20">
                                PROJECT: {currentProject?.toUpperCase()}
                            </div>

                            {/* Visualizer (centered) */}
                            <div className="flex-1 flex items-center justify-center relative min-h-0">
                                <div className="backdrop-blur-xl bg-black/30 border border-white/10 shadow-2xl rounded-2xl overflow-visible relative"
                                    style={{ width: Math.min(550, typeof window !== 'undefined' ? window.innerWidth * 0.7 : 550), height: 320 }}
                                >
                                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none mix-blend-overlay z-10 rounded-2xl" />
                                    <div className="relative z-20 w-full h-full flex items-center justify-center">
                                        <Visualizer
                                            audioData={aiAudioData}
                                            isListening={isConnected && !isMuted}
                                            intensity={audioAmp}
                                            width={Math.min(550, typeof window !== 'undefined' ? window.innerWidth * 0.7 : 550)}
                                            height={320}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* ============ ANCHORED CHAT (bottom) ============ */}
                            <div className="shrink-0 border-t border-cyan-500/10 bg-black/50 backdrop-blur-md">
                                {/* Messages area */}
                                <div className="max-w-3xl mx-auto px-4 pt-3">
                                    <div className="flex flex-col gap-2 overflow-y-auto scrollbar-hide mask-image-gradient" style={{ maxHeight: '180px' }}>
                                        {messages.slice(-8).map((msg, i) => (
                                            <div key={i} className="text-sm border-l-2 border-cyan-800/50 pl-3 py-1">
                                                <span className="text-cyan-600 font-mono text-xs opacity-70">[{msg.time}]</span>{' '}
                                                <span className="font-bold text-cyan-300 drop-shadow-sm">{msg.sender}</span>
                                                <div className="text-gray-300 mt-0.5 leading-relaxed">{msg.text}</div>
                                            </div>
                                        ))}
                                        <div ref={messagesEndRef} />
                                    </div>
                                </div>

                                {/* Input row */}
                                <div className="max-w-3xl mx-auto px-4 pb-3 pt-2">
                                    <div className="flex gap-2 items-center">
                                        <input
                                            type="text"
                                            value={inputValue}
                                            onChange={(e) => setInputValue(e.target.value)}
                                            onKeyDown={handleSendKey}
                                            placeholder="Type a message..."
                                            className="flex-1 bg-black/40 border border-cyan-700/30 rounded-lg px-4 py-2.5 text-cyan-50 text-sm focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all placeholder-cyan-800/50 backdrop-blur-sm"
                                        />

                                        {/* Mic Button */}
                                        <button
                                            onClick={toggleMute}
                                            disabled={!isConnected}
                                            className={`p-2.5 rounded-lg border transition-all duration-300 ${!isConnected
                                                ? 'border-gray-800 text-gray-800 cursor-not-allowed'
                                                : isMuted
                                                    ? 'border-red-500/50 bg-red-500/10 text-red-400 hover:bg-red-500/20 shadow-[0_0_10px_rgba(239,68,68,0.15)]'
                                                    : 'border-cyan-500/50 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 shadow-[0_0_10px_rgba(6,182,212,0.15)]'
                                            }`}
                                            title={isMuted ? 'Unmute mic' : 'Mute mic'}
                                        >
                                            {isMuted ? <MicOff size={18} /> : <Mic size={18} />}
                                        </button>

                                        {/* Send Button */}
                                        <button
                                            onClick={handleSendClick}
                                            disabled={!inputValue.trim()}
                                            className={`p-2.5 rounded-lg border transition-all duration-300 ${inputValue.trim()
                                                ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 shadow-[0_0_10px_rgba(6,182,212,0.15)]'
                                                : 'border-gray-800/50 text-gray-700 cursor-not-allowed'
                                            }`}
                                            title="Send message"
                                        >
                                            <Send size={18} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        /* Panel views */
                        <div className="flex-1 overflow-y-auto scrollbar-hide">
                            {activePanel === 'archive' && <KnowledgeArchivePanel socket={socket} />}
                            {activePanel === 'events' && <EventsPanel socket={socket} />}
                            {activePanel === 'quests' && <QuestsPanel socket={socket} />}
                            {activePanel === 'settings' && (
                                <SystemSettingsPanel
                                    socket={socket}
                                    micDevices={micDevices}
                                    speakerDevices={speakerDevices}
                                    webcamDevices={webcamDevices}
                                    selectedMicId={selectedMicId}
                                    setSelectedMicId={setSelectedMicId}
                                    selectedSpeakerId={selectedSpeakerId}
                                    setSelectedSpeakerId={setSelectedSpeakerId}
                                    selectedWebcamId={selectedWebcamId}
                                    setSelectedWebcamId={setSelectedWebcamId}
                                    cursorSensitivity={cursorSensitivity}
                                    setCursorSensitivity={setCursorSensitivity}
                                    isCameraFlipped={isCameraFlipped}
                                    setIsCameraFlipped={setIsCameraFlipped}
                                    handleFileUpload={handleFileUpload}
                                />
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* ============ OVERLAYS ============ */}
            {/* CAD Window */}
            {showCadWindow && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                    <div className="w-[480px] h-[480px] backdrop-blur-xl bg-black/60 border border-cyan-500/20 shadow-2xl rounded-2xl overflow-hidden flex flex-col">
                        <div className="h-8 bg-gray-900/80 border-b border-cyan-500/20 flex items-center justify-between px-3 shrink-0">
                            <span className="text-xs font-bold tracking-widest text-cyan-500/70">CAD PROTOTYPE</span>
                            <button onClick={() => setShowCadWindow(false)} className="text-gray-400 hover:text-red-400 p-1 rounded transition-colors">✕</button>
                        </div>
                        <div className="flex-1 min-h-0">
                            <CadWindow data={cadData} thoughts={cadThoughts} retryInfo={cadRetryInfo} onClose={() => setShowCadWindow(false)} socket={socket} />
                        </div>
                    </div>
                </div>
            )}

            {/* Browser Window */}
            {showBrowserWindow && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                    <div className="w-[600px] h-[420px] backdrop-blur-xl bg-black/60 border border-cyan-500/20 shadow-2xl rounded-2xl overflow-hidden">
                        <BrowserWindow imageSrc={browserData.image} logs={browserData.logs} onClose={() => setShowBrowserWindow(false)} socket={socket} />
                    </div>
                </div>
            )}

            {/* Tool Confirmation */}
            <ConfirmationPopup request={confirmationRequest} onConfirm={handleConfirmTool} onDeny={handleDenyTool} />

            {/* Reminder Alarm Overlay */}
            {alarmEvent && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-pulse-slow">
                    <div className="relative w-[420px] bg-gradient-to-br from-gray-900 via-gray-950 to-black border-2 border-amber-500/60 rounded-2xl shadow-[0_0_40px_rgba(245,158,11,0.2)] p-6 text-center">
                        <div className="text-5xl mb-3">⏰</div>
                        <h2 className="text-xl font-bold text-amber-300 tracking-wider mb-2">REMINDER</h2>
                        <p className="text-lg text-white font-semibold mb-1">{alarmEvent.title}</p>
                        {alarmEvent.notes && <p className="text-sm text-gray-400 mb-4">{alarmEvent.notes}</p>}
                        <button
                            onClick={() => {
                                socket.emit('reminder_alarm_dismissed', {
                                    event_id: alarmEvent.id,
                                    title: alarmEvent.title,
                                    dismissed_at_iso: new Date().toISOString(),
                                });
                                setAlarmEvent(null);
                            }}
                            className="mt-3 px-6 py-2 bg-amber-500/20 border border-amber-500/50 text-amber-300 rounded-lg hover:bg-amber-500/30 transition-colors text-sm font-bold tracking-wider"
                        >
                            DISMISS
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default AppTest;
