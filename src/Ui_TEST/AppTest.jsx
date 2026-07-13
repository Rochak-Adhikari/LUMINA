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
import FeaturesPanel from './panels/FeaturesPanel';
import BrowserWorkspacePanel from './panels/BrowserWorkspacePanel';

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

    // Auto-hide integrated browser views when navigating away from browser workspace
    useEffect(() => {
        if (activePanel !== 'browser') {
            ipcRenderer.send('browser-set-bounds', { visible: false });
        }
    }, [activePanel]);

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

        // Memory files (.txt) → upload as memory (existing behavior)
        const ext = file.name.split('.').pop()?.toLowerCase();
        if (ext === 'txt') {
            const reader = new FileReader();
            reader.onload = (event) => {
                const textContent = event.target.result;
                if (typeof textContent === 'string' && textContent.length > 0) {
                    socket.emit('upload_memory', { memory: textContent });
                    addMessage('System', 'Uploading memory...');
                }
            };
            reader.readAsText(file);
        } else {
            // All other file types → send path for AI file processing
            // For Electron, file.path gives the absolute path
            const filePath = file.path || file.name;
            socket.emit('process_file', { file_path: filePath, file_name: file.name });
            addMessage('System', `Processing file: ${file.name}...`);
        }
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
    };

    const audioAmp = aiAudioData.reduce((a, b) => a + b, 0) / aiAudioData.length / 255;

    // ========================================
    // RENDER
    // ========================================
    return (
        <div className="h-screen w-screen bg-[#030405] text-[#e2e2e4] font-manrope overflow-hidden flex flex-col relative selection:bg-primary-container/20 selection:text-primary">
            {/* Ambient Background Glows */}
            <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
                <div className="absolute top-[-20%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-primary opacity-[0.03] blur-[120px]" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[60vw] h-[60vw] rounded-full bg-secondary-fixed opacity-[0.02] blur-[150px]" />
            </div>

            {/* ============ TOP NAVIGATION HEADER ============ */}
            <nav className="fixed top-0 w-full flex justify-between items-center px-margin-desktop py-stack-md z-50 bg-transparent text-primary pointer-events-none" style={{ WebkitAppRegion: 'drag' }}>
                {/* Brand Logo */}
                <div 
                    className="font-sora text-2xl font-semibold tracking-tighter text-primary pointer-events-auto cursor-pointer active:scale-95 transition-transform"
                    onClick={() => navigateToPanel('home')}
                    style={{ WebkitAppRegion: 'no-drag' }}
                >
                    Lumina
                </div>

                {/* Status metrics & Window Controls */}
                <div className="flex items-center space-x-6 pointer-events-auto" style={{ WebkitAppRegion: 'no-drag' }}>
                    {/* Connection indicator */}
                    <div className="flex items-center space-x-2 font-mono-ui text-xs">
                        <span className={`w-2 h-2 rounded-full ${
                            connectionStatus === 'connected' ? 'bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]' :
                            connectionStatus === 'reconnecting' ? 'bg-yellow-400 animate-pulse' : 'bg-red-400'
                        }`} />
                        <span className="opacity-60 capitalize">{connectionStatus}</span>
                    </div>

                    {/* Quick alarm clock */}
                    <div className="flex items-center space-x-1.5 text-on-surface-variant font-mono-ui text-xs">
                        <Clock size={14} className="text-primary/50" />
                        <span>{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>

                    {/* Mic Toggle */}
                    <button 
                        onClick={toggleMute}
                        disabled={!isConnected}
                        className={`flex items-center justify-center p-1 rounded transition-colors ${
                            isMuted ? 'text-red-400 hover:text-red-300' : 'text-primary hover:text-primary-fixed-dim'
                        }`}
                        title={isMuted ? 'Unmute' : 'Mute'}
                    >
                        {isMuted ? <MicOff size={16} /> : <Mic size={16} />}
                    </button>

                    {/* Power Toggle */}
                    <button 
                        onClick={togglePower}
                        className={`flex items-center justify-center p-1 rounded transition-colors ${
                            isConnected ? 'text-green-400 hover:text-green-300' : 'text-on-surface-variant hover:text-white'
                        }`}
                        title={isConnected ? 'Disconnect' : 'Connect'}
                    >
                        <Power size={16} />
                    </button>

                    {/* Window control buttons */}
                    <div className="flex items-center space-x-1 border-l border-white/10 pl-4">
                        <button onClick={handleMinimize} className="p-1 hover:bg-white/5 rounded text-on-surface-variant hover:text-white transition-colors"><Minus size={16} /></button>
                        <button onClick={handleMaximize} className="p-1 hover:bg-white/5 rounded text-on-surface-variant hover:text-white transition-colors"><div className="w-[12px] h-[12px] border border-current rounded-[2px]" /></button>
                        <button onClick={handleCloseRequest} className="p-1 hover:bg-red-900/40 rounded text-red-500 hover:text-red-400 transition-colors"><X size={16} /></button>
                    </div>
                </div>
            </nav>

            {/* ============ SIDEBAR NAVIGATION DOCK ============ */}
            <Sidebar
                activePanel={activePanel}
                onNavigate={navigateToPanel}
            />

            {/* ============ MAIN CONTENT AREA ============ */}
            <main className="flex-1 min-h-screen relative z-10 ml-0 md:ml-[130px] pt-[120px] pb-8 px-8 flex flex-col w-full max-w-[1920px] mx-auto overflow-hidden">
                {/* Switch view between Home Dashboard and panel overlays */}
                {activePanel === 'home' ? (
                    <div className="flex-1 flex flex-col items-center justify-between w-full max-w-xl mx-auto py-4 min-h-[560px]">
                        {/* Project tracking Label */}
                        <div className="font-mono text-xs tracking-widest text-primary/60 uppercase">
                            PROJECT: {currentProject || 'Default'}
                        </div>

                        {/* Centerpiece visualizer orb */}
                        <div className="w-full max-w-[320px] aspect-square flex items-center justify-center relative float-subtle">
                            <Visualizer
                                audioData={aiAudioData}
                                isListening={isConnected && !isMuted}
                                intensity={audioAmp}
                                width={300}
                                height={300}
                            />
                            <div className="absolute inset-0 rounded-full shadow-[inset_0_0_60px_rgba(168,232,255,0.1)] pointer-events-none" />
                        </div>

                        {/* VAD / State Wave indicator */}
                        <div className="flex items-center space-x-3 bg-[#080B0E]/80 backdrop-blur-md px-5 py-2.5 rounded-full border border-white/5 shadow-xl">
                            <div className="flex items-center space-x-1 h-5">
                                <div className="waveform-bar"></div>
                                <div className="waveform-bar"></div>
                                <div className="waveform-bar"></div>
                                <div className="waveform-bar"></div>
                                <div className="waveform-bar"></div>
                            </div>
                            <span className="font-mono text-xs tracking-widest text-primary uppercase">
                                {isConnected ? (isMuted ? 'Muted' : 'Listening...') : 'Offline'}
                            </span>
                        </div>

                        {/* Transcript timeline logs preview */}
                        <div className="w-full h-[140px] overflow-y-auto scrollbar-hide space-y-2 py-1 mask-image-gradient">
                            {messages.slice(-4).map((msg, i) => (
                                <div 
                                    key={i} 
                                    className={`glass-level-2 rounded-xl p-3 border-l-2 relative overflow-hidden transition-all duration-300 ${
                                        msg.sender === 'You' ? 'border-l-primary/70' : 'border-l-secondary-fixed/70'
                                    }`}
                                >
                                    <div className="flex justify-between items-center text-[10px] text-on-surface-variant opacity-60 font-mono">
                                        <span>{msg.sender}</span>
                                        <span>{msg.time}</span>
                                    </div>
                                    <p className="font-manrope text-xs text-on-surface mt-0.5 leading-relaxed">
                                        {msg.text}
                                    </p>
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Floating bottom voice/text controller with integrated Mic button */}
                        <div className="w-full flex gap-2 items-center bg-white/5 border border-white/10 rounded-full px-4 py-2.5 backdrop-blur-md shadow-2xl mt-2">
                            <input
                                type="text"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={handleSendKey}
                                placeholder="Type a command or ask Luna anything..."
                                className="flex-1 bg-transparent border-0 outline-none text-white text-xs placeholder-on-surface-variant/40 focus:ring-0"
                            />

                            {/* File Attachments selector */}
                            <label className="p-2 rounded-full hover:bg-white/10 text-on-surface-variant hover:text-primary transition-colors cursor-pointer" title="Process file">
                                <input type="file" onChange={handleFileUpload} className="hidden" />
                                <span className="material-symbols-outlined text-[18px]">attach_file</span>
                            </label>

                            {/* Integrated Mic Button inside chat row */}
                            <button
                                onClick={toggleMute}
                                disabled={!isConnected}
                                className={`p-2 rounded-full border transition-all duration-300 ${
                                    !isConnected
                                        ? 'border-transparent text-on-surface-variant/20'
                                        : isMuted
                                            ? 'border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 shadow-[0_0_8px_rgba(239,68,68,0.15)]'
                                            : 'border-primary-container/30 bg-primary-container/10 text-primary hover:bg-primary-container/20 shadow-[0_0_8px_rgba(6,182,212,0.15)]'
                                }`}
                                title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
                            >
                                {isMuted ? <MicOff size={14} /> : <Mic size={14} />}
                            </button>

                            {/* Send Button */}
                            <button
                                onClick={handleSendClick}
                                disabled={!inputValue.trim()}
                                className={`p-2 rounded-full border transition-all duration-300 ${
                                    inputValue.trim()
                                        ? 'border-primary-container/40 bg-primary-container/20 text-primary hover:scale-105 shadow-[0_0_8px_rgba(6,182,212,0.15)]'
                                        : 'border-transparent text-on-surface-variant/20'
                                }`}
                            >
                                <Send size={14} />
                            </button>
                        </div>
                    </div>
                ) : (
                    /* Render other navigation overlays/panels */
                    <div className={`flex-1 relative z-10 w-full mx-auto ${
                        activePanel === 'browser' ? 'h-[calc(100vh-160px)] overflow-hidden' : 'overflow-y-auto scrollbar-hide pb-12 max-w-[1400px]'
                    }`}>
                        {activePanel === 'browser' && (
                            <BrowserWorkspacePanel
                                socket={socket}
                                aiAudioData={aiAudioData}
                                isConnected={isConnected}
                                isMuted={isMuted}
                                messages={messages}
                                toggleMute={toggleMute}
                                handleSendClick={handleSendClick}
                                handleSendKey={handleSendKey}
                                inputValue={inputValue}
                                setInputValue={setInputValue}
                                messagesEndRef={messagesEndRef}
                                audioAmp={audioAmp}
                            />
                        )}
                        {activePanel === 'archive' && <KnowledgeArchivePanel socket={socket} />}
                        {activePanel === 'events' && <EventsPanel socket={socket} />}
                        {activePanel === 'quests' && <QuestsPanel socket={socket} />}
                        {activePanel === 'features' && <FeaturesPanel />}
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
            </main>

            {/* ============ MODAL WINDOW OVERLAYS ============ */}
            {/* CAD Window */}
            {showCadWindow && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
                    <div className="w-[520px] h-[520px] backdrop-blur-2xl bg-black/60 border border-cyan-500/20 shadow-2xl rounded-2xl overflow-hidden flex flex-col">
                        <div className="h-10 bg-black/80 border-b border-cyan-500/25 flex items-center justify-between px-4 shrink-0">
                            <span className="font-mono text-xs font-bold tracking-widest text-primary">CAD PROTOTYPER VIEW</span>
                            <button onClick={() => setShowCadWindow(false)} className="text-on-surface-variant hover:text-red-400 text-sm transition-colors">✕</button>
                        </div>
                        <div className="flex-1 min-h-0">
                            <CadWindow data={cadData} thoughts={cadThoughts} retryInfo={cadRetryInfo} onClose={() => setShowCadWindow(false)} socket={socket} />
                        </div>
                    </div>
                </div>
            )}

            {/* Browser Window */}
            {showBrowserWindow && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
                    <div className="w-[700px] h-[480px] backdrop-blur-2xl bg-black/60 border border-cyan-500/20 shadow-2xl rounded-2xl overflow-hidden">
                        <BrowserWindow imageSrc={browserData.image} logs={browserData.logs} onClose={() => setShowBrowserWindow(false)} socket={socket} />
                    </div>
                </div>
            )}

            {/* Tool Action Confirmation Popup */}
            <ConfirmationPopup request={confirmationRequest} onConfirm={handleConfirmTool} onDeny={handleDenyTool} />

            {/* Reminder Alarm Overlay */}
            {alarmEvent && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-md animate-pulse-slow">
                    <div className="relative w-[440px] bg-gradient-to-br from-[#0c0d10] via-[#121415] to-[#0d0e10] border-2 border-amber-500/50 rounded-2xl shadow-[0_0_50px_rgba(245,158,11,0.25)] p-6 text-center">
                        <div className="text-5xl mb-4">⏰</div>
                        <h2 className="font-sora text-xl font-semibold text-amber-300 tracking-wider mb-2">REMINDER ALERT</h2>
                        <p className="font-body-lg text-lg text-white font-bold mb-1">{alarmEvent.title}</p>
                        {alarmEvent.notes && <p className="font-manrope text-sm text-on-surface-variant/70 mb-4">{alarmEvent.notes}</p>}
                        <button
                            onClick={() => {
                                socket.emit('reminder_alarm_dismissed', {
                                    event_id: alarmEvent.id,
                                    title: alarmEvent.title,
                                    dismissed_at_iso: new Date().toISOString(),
                                });
                                setAlarmEvent(null);
                            }}
                            className="mt-2 px-8 py-2.5 bg-amber-500/10 border border-amber-500/40 text-amber-300 rounded-full hover:bg-amber-500/20 transition-all text-xs font-bold tracking-widest"
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
