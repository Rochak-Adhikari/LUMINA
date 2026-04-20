import React, { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';

const TOOLS = [
    { id: 'generate_cad', label: 'Generate CAD' },
    { id: 'local_browser_control', label: 'Local Browser (Brave)' },
    { id: 'browser_control', label: 'Browser Agent (headless)' },
    { id: 'create_directory', label: 'Create Folder' },
    { id: 'write_file', label: 'Write File' },
    { id: 'read_directory', label: 'Read Directory' },
    { id: 'read_file', label: 'Read File' },
    { id: 'create_project', label: 'Create Project' },
    { id: 'switch_project', label: 'Switch Project' },
    { id: 'list_projects', label: 'List Projects' },
    { id: 'list_smart_devices', label: 'List Devices' },
    { id: 'control_light', label: 'Control Light' },
    { id: 'discover_printers', label: 'Discover Printers' },
    { id: 'print_stl', label: 'Print 3D Model' },
    { id: 'iterate_cad', label: 'Iterate CAD' },
];

const SettingsWindow = ({
    socket,
    micDevices,
    speakerDevices,
    webcamDevices,
    selectedMicId,
    setSelectedMicId,
    selectedSpeakerId,
    setSelectedSpeakerId,
    selectedWebcamId,
    setSelectedWebcamId,
    cursorSensitivity,
    setCursorSensitivity,
    isCameraFlipped,
    setIsCameraFlipped,
    handleFileUpload,
    onClose
}) => {
    const [permissions, setPermissions] = useState({});
    const [faceAuthEnabled, setFaceAuthEnabled] = useState(false);
    const [confirmationMode, setConfirmationMode] = useState('relaxed');
    const [lastBrowserAction, setLastBrowserAction] = useState(null);
    const [personaEnabled, setPersonaEnabled] = useState(true);
    const [personaMode, setPersonaMode] = useState('playful_mischievous_best_friend');
    const [teasingIntensity, setTeasingIntensity] = useState(0.6);
    const [idleEnabled, setIdleEnabled] = useState(true);
    const [strictSensitivity, setStrictSensitivity] = useState(0.5);
    const [adaptiveMode, setAdaptiveMode] = useState(true);
    const hasHydratedRef = useRef(false);

    useEffect(() => {
        // Request initial permissions
        socket.emit('get_settings');

        // Listen for updates
        const handleSettings = (settings) => {
            console.log("Received settings:", settings);
            if (settings) {
                if (settings.tool_permissions) setPermissions(settings.tool_permissions);
                if (typeof settings.face_auth_enabled !== 'undefined') {
                    setFaceAuthEnabled(settings.face_auth_enabled);
                    localStorage.setItem('face_auth_enabled', settings.face_auth_enabled);
                }
                if (settings.browser_confirmation_mode) {
                    setConfirmationMode(settings.browser_confirmation_mode);
                }
                if (typeof settings.persona_enabled !== 'undefined') setPersonaEnabled(settings.persona_enabled);
                if (settings.persona_mode) setPersonaMode(settings.persona_mode);
                if (typeof settings.persona_teasing_intensity !== 'undefined') setTeasingIntensity(settings.persona_teasing_intensity);
                if (typeof settings.persona_idle_enabled !== 'undefined') setIdleEnabled(settings.persona_idle_enabled);
                if (typeof settings.persona_strict_sensitivity !== 'undefined') setStrictSensitivity(settings.persona_strict_sensitivity);
                if (typeof settings.persona_adaptive_mode !== 'undefined') setAdaptiveMode(settings.persona_adaptive_mode);
                hasHydratedRef.current = true;
                console.debug('[SETTINGS] Hydrated from backend:', settings);
            }
        };

        socket.on('settings', handleSettings);
        // Also listen for legacy tool_permissions if needed, but 'settings' covers it
        // socket.on('tool_permissions', handlePermissions); 

        return () => {
            socket.off('settings', handleSettings);
        };
    }, [socket]);

    const togglePermission = (toolId) => {
        if (!hasHydratedRef.current) {
            console.warn('[SETTINGS] togglePermission blocked — not hydrated yet');
            return;
        }
        const currentVal = permissions[toolId] !== false; // Default True
        const nextVal = !currentVal;

        const payload = { tool_permissions: { [toolId]: nextVal } };
        console.debug('[SETTINGS EMIT]', payload, new Error().stack);
        socket.emit('update_settings', payload);
    };

    const toggleFaceAuth = () => {
        if (!hasHydratedRef.current) return;
        const newVal = !faceAuthEnabled;
        setFaceAuthEnabled(newVal);
        localStorage.setItem('face_auth_enabled', newVal);
        const payload = { face_auth_enabled: newVal };
        console.debug('[SETTINGS EMIT]', payload, new Error().stack);
        socket.emit('update_settings', payload);
    };

    const toggleCameraFlip = () => {
        if (!hasHydratedRef.current) return;
        const newVal = !isCameraFlipped;
        setIsCameraFlipped(newVal);
        const payload = { camera_flipped: newVal };
        console.debug('[SETTINGS EMIT]', payload, new Error().stack);
        socket.emit('update_settings', payload);
    };

    return (
        <div className="absolute top-20 right-10 bg-black/90 border border-cyan-500/50 p-4 rounded-lg z-50 w-80 backdrop-blur-xl shadow-[0_0_30px_rgba(6,182,212,0.2)]">
            <div className="flex justify-between items-center mb-4 border-b border-cyan-900/50 pb-2">
                <h2 className="text-cyan-400 font-bold text-sm uppercase tracking-wider">Settings</h2>
                <button onClick={onClose} className="text-cyan-600 hover:text-cyan-400">
                    <X size={16} />
                </button>
            </div>

            {/* Authentication Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Security</h3>
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                    <span className="text-cyan-100/80">Face Authentication</span>
                    <button
                        onClick={toggleFaceAuth}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${faceAuthEnabled ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                    >
                        <div
                            className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${faceAuthEnabled ? 'translate-x-4' : 'translate-x-0'}`}
                        />
                    </button>
                </div>
            </div>

            {/* Microphone Section */}
            <div className="mb-4">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Microphone</h3>
                <select
                    value={selectedMicId}
                    onChange={(e) => setSelectedMicId(e.target.value)}
                    className="w-full bg-gray-900 border border-cyan-800 rounded p-2 text-xs text-cyan-100 focus:border-cyan-400 outline-none"
                >
                    {micDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Microphone ${i + 1}`}
                        </option>
                    ))}
                </select>
            </div>

            {/* Speaker Section */}
            <div className="mb-4">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Speaker</h3>
                <select
                    value={selectedSpeakerId}
                    onChange={(e) => setSelectedSpeakerId(e.target.value)}
                    className="w-full bg-gray-900 border border-cyan-800 rounded p-2 text-xs text-cyan-100 focus:border-cyan-400 outline-none"
                >
                    {speakerDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Speaker ${i + 1}`}
                        </option>
                    ))}
                </select>
            </div>

            {/* Webcam Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Webcam</h3>
                <select
                    value={selectedWebcamId}
                    onChange={(e) => setSelectedWebcamId(e.target.value)}
                    className="w-full bg-gray-900 border border-cyan-800 rounded p-2 text-xs text-cyan-100 focus:border-cyan-400 outline-none"
                >
                    {webcamDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Camera ${i + 1}`}
                        </option>
                    ))}
                </select>
            </div>

            {/* Cursor Section */}
            <div className="mb-6">
                <div className="flex justify-between mb-2">
                    <h3 className="text-cyan-400 font-bold text-xs uppercase tracking-wider opacity-80">Cursor Sensitivity</h3>
                    <span className="text-xs text-cyan-500">{cursorSensitivity}x</span>
                </div>
                <input
                    type="range"
                    min="1.0"
                    max="5.0"
                    step="0.1"
                    value={cursorSensitivity}
                    onChange={(e) => setCursorSensitivity(parseFloat(e.target.value))}
                    className="w-full accent-cyan-400 cursor-pointer h-1 bg-gray-800 rounded-lg appearance-none"
                />
            </div>

            {/* Gesture Control Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Gesture Control</h3>
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                    <span className="text-cyan-100/80">Flip Camera Horizontal</span>
                    <button
                        onClick={toggleCameraFlip}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${isCameraFlipped ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                    >
                        <div
                            className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${isCameraFlipped ? 'translate-x-4' : 'translate-x-0'}`}
                        />
                    </button>
                </div>
            </div>

            {/* Browser Control Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Browser Control</h3>

                {/* Confirmation Mode Selector */}
                <div className="text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30 mb-2">
                    <span className="text-cyan-100/80 block mb-2">Confirmation Mode</span>
                    <div className="flex gap-1">
                        {['strict', 'relaxed', 'off'].map(mode => (
                            <button
                                key={mode}
                                onClick={() => {
                                    if (!hasHydratedRef.current) return;
                                    setConfirmationMode(mode);
                                    const payload = { browser_confirmation_mode: mode };
                                    console.debug('[SETTINGS EMIT]', payload);
                                    socket.emit('update_settings', payload);
                                }}
                                className={`flex-1 py-1 px-2 rounded text-[10px] font-medium transition-colors ${
                                    confirmationMode === mode
                                        ? mode === 'strict' ? 'bg-red-500/80 text-white'
                                          : mode === 'relaxed' ? 'bg-cyan-500/80 text-white'
                                          : 'bg-yellow-500/80 text-black'
                                        : 'bg-gray-800 text-cyan-300/60 hover:bg-gray-700'
                                }`}
                            >
                                {mode.charAt(0).toUpperCase() + mode.slice(1)}
                            </button>
                        ))}
                    </div>
                    <p className="text-[10px] text-cyan-500/40 mt-1">
                        {confirmationMode === 'strict' ? 'All interactive actions require confirmation'
                         : confirmationMode === 'relaxed' ? 'Only typing & dangerous actions need confirmation'
                         : 'No confirmations except dangerous content (send, delete, pay...)'}
                    </p>
                </div>

                {/* Last Browser Action */}
                {lastBrowserAction && (
                    <div className="text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30 mb-2">
                        <span className="text-cyan-100/60 block text-[10px]">Last Action</span>
                        <span className={`text-[11px] ${lastBrowserAction.ok ? 'text-green-400' : 'text-red-400'}`}>
                            {lastBrowserAction.action}: {lastBrowserAction.message?.substring(0, 80)}
                        </span>
                    </div>
                )}

                {/* Emergency Kill Switch */}
                <button
                    onClick={() => {
                        socket.emit('kill_browser_tools');
                        setLastBrowserAction({ action: 'KILLED', ok: false, message: 'All browser tools disabled' });
                    }}
                    className="w-full py-1.5 px-3 rounded text-xs font-bold bg-red-900/60 text-red-300 border border-red-700/50 hover:bg-red-800/80 hover:text-red-100 transition-colors"
                >
                    ⛔ Emergency Kill — Disable All Browser Tools
                </button>
            </div>

            {/* Persona Engine Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Persona Engine</h3>

                {/* Enable/Disable Toggle */}
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30 mb-2">
                    <span className="text-cyan-100/80">Persona Active</span>
                    <button
                        onClick={() => {
                            if (!hasHydratedRef.current) return;
                            const val = !personaEnabled;
                            setPersonaEnabled(val);
                            socket.emit('update_settings', { persona_enabled: val });
                        }}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${personaEnabled ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                    >
                        <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${personaEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
                    </button>
                </div>

                {/* Adaptive Mode Checkbox */}
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30 mb-2">
                    <div>
                        <span className="text-cyan-100/80">Adaptive Mode</span>
                        <span className="text-[10px] text-cyan-500/40 ml-1">(recommended)</span>
                    </div>
                    <button
                        onClick={() => {
                            if (!hasHydratedRef.current) return;
                            const val = !adaptiveMode;
                            setAdaptiveMode(val);
                            socket.emit('update_settings', { persona_adaptive_mode: val });
                        }}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${adaptiveMode ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                    >
                        <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${adaptiveMode ? 'translate-x-4' : 'translate-x-0'}`} />
                    </button>
                </div>

                {/* Mode Dropdown (bias when adaptive) */}
                <div className="text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30 mb-2">
                    <span className="text-cyan-100/80 block mb-1">{adaptiveMode ? 'Style Bias' : 'Mode'}</span>
                    <select
                        value={personaMode}
                        onChange={(e) => {
                            if (!hasHydratedRef.current) return;
                            setPersonaMode(e.target.value);
                            socket.emit('update_settings', { persona_mode: e.target.value });
                        }}
                        className="w-full bg-gray-800 text-cyan-200 text-[11px] rounded px-2 py-1 border border-cyan-900/30 focus:outline-none"
                    >
                        <option value="playful_mischievous_best_friend">Playful Best Friend</option>
                        <option value="calm_supportive">Calm & Supportive</option>
                        <option value="professional">Professional</option>
                    </select>
                    {adaptiveMode && <p className="text-[10px] text-cyan-500/40 mt-1">Adaptive adjusts tone automatically — this is a starting bias only</p>}
                </div>

                {/* Teasing Cap Slider */}
                <div className="text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30 mb-2">
                    <div className="flex justify-between mb-1">
                        <span className="text-cyan-100/80">{adaptiveMode ? 'Max Teasing Cap' : 'Teasing Intensity'}</span>
                        <span className="text-cyan-400/60 text-[10px]">{Math.round(teasingIntensity * 100)}%</span>
                    </div>
                    <input
                        type="range" min="0" max="100" step="5"
                        value={Math.round(teasingIntensity * 100)}
                        onChange={(e) => {
                            if (!hasHydratedRef.current) return;
                            const val = parseInt(e.target.value) / 100;
                            setTeasingIntensity(val);
                            socket.emit('update_settings', { persona_teasing_intensity: val });
                        }}
                        className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                </div>

                {/* Idle Check-in Toggle */}
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30 mb-2">
                    <span className="text-cyan-100/80">Idle Check-ins</span>
                    <button
                        onClick={() => {
                            if (!hasHydratedRef.current) return;
                            const val = !idleEnabled;
                            setIdleEnabled(val);
                            socket.emit('update_settings', { persona_idle_enabled: val });
                        }}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${idleEnabled ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                    >
                        <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${idleEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
                    </button>
                </div>

                {/* Strict Mode Sensitivity Slider */}
                <div className="text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                    <div className="flex justify-between mb-1">
                        <span className="text-cyan-100/80">Strict Mode Sensitivity</span>
                        <span className="text-cyan-400/60 text-[10px]">{Math.round(strictSensitivity * 100)}%</span>
                    </div>
                    <input
                        type="range" min="10" max="100" step="10"
                        value={Math.round(strictSensitivity * 100)}
                        onChange={(e) => {
                            if (!hasHydratedRef.current) return;
                            const val = parseInt(e.target.value) / 100;
                            setStrictSensitivity(val);
                            socket.emit('update_settings', { persona_strict_sensitivity: val });
                        }}
                        className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                    <p className="text-[10px] text-cyan-500/40 mt-1">Higher = triggers strict mode more easily on self-destructive patterns</p>
                </div>
            </div>

            {/* Tool Permissions Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Tool Confirmations</h3>
                <div className="space-y-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                    {TOOLS.map(tool => {
                        const isRequired = permissions[tool.id] !== false; // Default True
                        return (
                            <div key={tool.id} className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                                <span className="text-cyan-100/80">{tool.label}</span>
                                <button
                                    onClick={() => togglePermission(tool.id)}
                                    className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${isRequired ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                                >
                                    <div
                                        className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${isRequired ? 'translate-x-4' : 'translate-x-0'}`}
                                    />
                                </button>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Memory Section */}
            <div>
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Memory Data</h3>
                <div className="flex flex-col gap-2">
                    <label className="text-[10px] text-cyan-500/60 uppercase">Upload Memory Text</label>
                    <input
                        type="file"
                        accept=".txt"
                        onChange={handleFileUpload}
                        className="text-xs text-cyan-100 bg-gray-900 border border-cyan-800 rounded p-2 file:mr-2 file:py-1 file:px-2 file:rounded-full file:border-0 file:text-[10px] file:font-semibold file:bg-cyan-900 file:text-cyan-400 hover:file:bg-cyan-800 cursor-pointer"
                    />
                </div>
            </div>
        </div>
    );
};

export default SettingsWindow;
