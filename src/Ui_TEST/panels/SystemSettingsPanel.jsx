import React, { useState, useEffect, useRef, useCallback } from 'react';

const TOOLS = [
    { id: 'local_browser_control', label: 'Local Browser (Brave)' },
    { id: 'browser_control', label: 'Browser Agent (headless)' },
    { id: 'create_directory', label: 'Create Folder' },
    { id: 'write_file', label: 'Write File' },
    { id: 'read_directory', label: 'Read Directory' },
    { id: 'read_file', label: 'Read File' },
    { id: 'create_project', label: 'Create Project' },
    { id: 'switch_project', label: 'Switch Project' },
    { id: 'list_projects', label: 'List Projects' },
];

const Toggle = ({ value, onChange, disabled }) => (
    <button
        onClick={onChange}
        disabled={disabled}
        className={`relative w-9 h-5 rounded-full transition-colors duration-200 shrink-0 ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'} ${value ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
    >
        <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform duration-200 ${value ? 'translate-x-4' : 'translate-x-0'}`} />
    </button>
);

const SliderRow = ({ label, value, min, max, step, suffix, onChange, disabled }) => (
    <div className="flex items-center justify-between gap-4">
        <span className="text-xs text-cyan-100/80 shrink-0">{label}</span>
        <div className="flex items-center gap-2 flex-1 max-w-[200px]">
            <input
                type="range"
                min={min} max={max} step={step}
                value={value}
                onChange={onChange}
                disabled={disabled}
                className="flex-1 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
            <span className="text-[10px] text-cyan-400/60 w-10 text-right font-mono">{value}{suffix}</span>
        </div>
    </div>
);

const ToggleRow = ({ label, value, onChange, disabled, hint }) => (
    <div className="flex items-center justify-between gap-2">
        <div className="flex-1 min-w-0">
            <span className="text-xs text-cyan-100/80">{label}</span>
            {hint && <span className="text-[10px] text-cyan-500/40 ml-1">({hint})</span>}
        </div>
        <Toggle value={value} onChange={onChange} disabled={disabled} />
    </div>
);

const SectionCard = ({ title, children, color = 'cyan' }) => {
    const borderColor = color === 'cyan' ? 'border-cyan-500/25' : color === 'red' ? 'border-red-500/25' : 'border-purple-500/25';
    const titleColor = color === 'cyan' ? 'text-cyan-400' : color === 'red' ? 'text-red-400' : 'text-purple-400';
    const glowColor = color === 'cyan' ? 'shadow-[0_0_15px_rgba(6,182,212,0.06)]' : color === 'red' ? 'shadow-[0_0_15px_rgba(239,68,68,0.06)]' : 'shadow-[0_0_15px_rgba(168,85,247,0.06)]';

    return (
        <div className={`border ${borderColor} bg-black/30 backdrop-blur-sm rounded-xl p-5 ${glowColor}`}>
            <h3 className={`text-sm font-bold ${titleColor} tracking-widest uppercase mb-4`}>{title}</h3>
            <div className="flex flex-col gap-3">
                {children}
            </div>
        </div>
    );
};

const SystemSettingsPanel = ({ socket, micDevices, speakerDevices, webcamDevices, selectedMicId, setSelectedMicId, selectedSpeakerId, setSelectedSpeakerId, selectedWebcamId, setSelectedWebcamId, cursorSensitivity, setCursorSensitivity, isCameraFlipped, setIsCameraFlipped, handleFileUpload }) => {
    const [permissions, setPermissions] = useState({});
    const [clampMode, setClampMode] = useState('off');
    const [clampAllowlist, setClampAllowlist] = useState([]);
    const [faceAuthEnabled, setFaceAuthEnabled] = useState(false);
    const [confirmationMode, setConfirmationMode] = useState('relaxed');
    const [personaEnabled, setPersonaEnabled] = useState(true);
    const [personaMode, setPersonaMode] = useState('playful_mischievous_best_friend');
    const [teasingIntensity, setTeasingIntensity] = useState(60);
    const [idleEnabled, setIdleEnabled] = useState(true);
    const [strictSensitivity, setStrictSensitivity] = useState(50);
    const [adaptiveMode, setAdaptiveMode] = useState(true);
    const [remotePairing, setRemotePairing] = useState(null);
    const [pinCopied, setPinCopied] = useState(false);
    const hasHydratedRef = useRef(false);

    useEffect(() => {
        socket.emit('get_settings');

        const handleSettings = (settings) => {
            if (!settings) return;
            if (settings.tool_permissions) setPermissions(settings.tool_permissions);
            if (settings._tool_clamp_mode) setClampMode(settings._tool_clamp_mode);
            if (settings._tool_clamp_allowlist) setClampAllowlist(settings._tool_clamp_allowlist);
            if (typeof settings.face_auth_enabled !== 'undefined') setFaceAuthEnabled(settings.face_auth_enabled);
            if (settings.browser_confirmation_mode) setConfirmationMode(settings.browser_confirmation_mode);
            if (typeof settings.persona_enabled !== 'undefined') setPersonaEnabled(settings.persona_enabled);
            if (settings.persona_mode) setPersonaMode(settings.persona_mode);
            if (typeof settings.persona_teasing_intensity !== 'undefined') setTeasingIntensity(Math.round(settings.persona_teasing_intensity * 100));
            if (typeof settings.persona_idle_enabled !== 'undefined') setIdleEnabled(settings.persona_idle_enabled);
            if (typeof settings.persona_strict_sensitivity !== 'undefined') setStrictSensitivity(Math.round(settings.persona_strict_sensitivity * 100));
            if (typeof settings.persona_adaptive_mode !== 'undefined') setAdaptiveMode(settings.persona_adaptive_mode);
            if (settings.remote_pairing) setRemotePairing(settings.remote_pairing);
            hasHydratedRef.current = true;
        };

        socket.on('settings', handleSettings);
        return () => socket.off('settings', handleSettings);
    }, [socket]);

    const emit = (payload) => {
        if (!hasHydratedRef.current) return;
        socket.emit('update_settings', payload);
    };

    const refreshPairing = useCallback(() => {
        // Re-request settings which rotates the PIN
        socket.emit('get_settings');
    }, [socket]);

    const copyPin = useCallback(() => {
        if (!remotePairing?.pin) return;
        navigator.clipboard.writeText(remotePairing.pin).then(() => {
            setPinCopied(true);
            setTimeout(() => setPinCopied(false), 2000);
        });
    }, [remotePairing]);

    const revokeDevices = useCallback(() => {
        socket.emit('revoke_remote_devices');
        setTimeout(refreshPairing, 300);
    }, [socket, refreshPairing]);

    const isToolClamped = (toolId) => {
        if (clampMode !== 'on') return false;
        return true; // When clamp is on, all tools are policy-controlled
    };

    const togglePermission = (toolId) => {
        if (!hasHydratedRef.current) return;
        if (isToolClamped(toolId)) return; // Don't allow toggle when clamped
        const current = !!permissions[toolId];
        emit({ tool_permissions: { [toolId]: !current } });
    };

    return (
        <div className="p-6 max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-bold text-cyan-200 tracking-widest">System Settings</h2>
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full border border-cyan-500/40 flex items-center justify-center shadow-[0_0_12px_rgba(6,182,212,0.15)]">
                        <span className="text-xs font-bold text-cyan-400">L</span>
                    </div>
                    <span className="text-[10px] text-cyan-600 tracking-wider">LUNA — SYSTEM CONFIG</span>
                </div>
            </div>

            {/* Grid Layout — matching the reference image */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">

                {/* ══════ PERSONA ══════ */}
                <SectionCard title="Persona" color="cyan">
                    <ToggleRow label="Persona Active" value={personaEnabled} onChange={() => { setPersonaEnabled(!personaEnabled); emit({ persona_enabled: !personaEnabled }); }} />
                    <ToggleRow label="Adaptive Mode" value={adaptiveMode} hint="recommended" onChange={() => { setAdaptiveMode(!adaptiveMode); emit({ persona_adaptive_mode: !adaptiveMode }); }} />

                    <div>
                        <span className="text-xs text-cyan-100/80 block mb-1.5">{adaptiveMode ? 'Style Bias' : 'Mode'}</span>
                        <select
                            value={personaMode}
                            onChange={(e) => { setPersonaMode(e.target.value); emit({ persona_mode: e.target.value }); }}
                            className="w-full bg-gray-900/80 text-cyan-200 text-xs rounded-lg px-3 py-2 border border-cyan-800/40 focus:outline-none focus:border-cyan-500/50 transition-colors"
                        >
                            <option value="playful_mischievous_best_friend">Playful Best Friend</option>
                            <option value="calm_supportive">Calm &amp; Supportive</option>
                            <option value="professional">Professional</option>
                        </select>
                    </div>

                    <SliderRow label={adaptiveMode ? 'Max Teasing Cap' : 'Teasing Intensity'} value={teasingIntensity} min={0} max={100} step={5} suffix="%" onChange={(e) => { const v = parseInt(e.target.value); setTeasingIntensity(v); emit({ persona_teasing_intensity: v / 100 }); }} />
                    <SliderRow label="Strict Mode Sensitivity" value={strictSensitivity} min={10} max={100} step={10} suffix="%" onChange={(e) => { const v = parseInt(e.target.value); setStrictSensitivity(v); emit({ persona_strict_sensitivity: v / 100 }); }} />
                    <ToggleRow label="Idle Check-ins" value={idleEnabled} onChange={() => { setIdleEnabled(!idleEnabled); emit({ persona_idle_enabled: !idleEnabled }); }} />
                </SectionCard>

                {/* ══════ AUDIO / DEVICES ══════ */}
                <SectionCard title="Audio" color="cyan">
                    <div>
                        <span className="text-xs text-cyan-100/80 block mb-1.5">Microphone</span>
                        <select value={selectedMicId} onChange={(e) => setSelectedMicId(e.target.value)} className="w-full bg-gray-900/80 text-cyan-200 text-xs rounded-lg px-3 py-2 border border-cyan-800/40 focus:outline-none focus:border-cyan-500/50 transition-colors">
                            {micDevices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Microphone ${i + 1}`}</option>)}
                        </select>
                    </div>
                    <div>
                        <span className="text-xs text-cyan-100/80 block mb-1.5">Speaker</span>
                        <select value={selectedSpeakerId} onChange={(e) => setSelectedSpeakerId(e.target.value)} className="w-full bg-gray-900/80 text-cyan-200 text-xs rounded-lg px-3 py-2 border border-cyan-800/40 focus:outline-none focus:border-cyan-500/50 transition-colors">
                            {speakerDevices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Speaker ${i + 1}`}</option>)}
                        </select>
                    </div>
                    <div>
                        <span className="text-xs text-cyan-100/80 block mb-1.5">Webcam</span>
                        <select value={selectedWebcamId} onChange={(e) => setSelectedWebcamId(e.target.value)} className="w-full bg-gray-900/80 text-cyan-200 text-xs rounded-lg px-3 py-2 border border-cyan-800/40 focus:outline-none focus:border-cyan-500/50 transition-colors">
                            {webcamDevices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Camera ${i + 1}`}</option>)}
                        </select>
                    </div>
                    <SliderRow label="Cursor Sensitivity" value={cursorSensitivity} min={1.0} max={5.0} step={0.1} suffix="x" onChange={(e) => setCursorSensitivity(parseFloat(e.target.value))} />
                </SectionCard>

                {/* ══════ TOOLS ══════ */}
                <SectionCard title="Tools" color="cyan">
                    {clampMode === 'on' && (
                        <div className="px-3 py-2 rounded-lg border border-yellow-500/30 bg-yellow-500/5 text-yellow-400 text-[10px] mb-1">
                            Policy clamp active — tools are enforced by server config.
                            {clampAllowlist.length > 0 && <span className="text-yellow-500/60"> Allowed: {clampAllowlist.join(', ')}</span>}
                        </div>
                    )}
                    <div className="flex flex-col gap-2.5 max-h-[280px] overflow-y-auto scrollbar-hide pr-1">
                        {TOOLS.map(tool => {
                            const isEnabled = !!permissions[tool.id];
                            const clamped = isToolClamped(tool.id);
                            return (
                                <ToggleRow key={tool.id} label={tool.label} value={isEnabled} onChange={() => togglePermission(tool.id)}
                                    disabled={clamped} hint={clamped ? 'policy' : undefined} />
                            );
                        })}
                    </div>
                </SectionCard>

                {/* ══════ SECURITY ══════ */}
                <SectionCard title="Security" color="cyan">
                    <ToggleRow label="Face Authentication" value={faceAuthEnabled} onChange={() => { const v = !faceAuthEnabled; setFaceAuthEnabled(v); localStorage.setItem('face_auth_enabled', v); emit({ face_auth_enabled: v }); }} />
                    <ToggleRow label="Camera Flip (Horizontal)" value={isCameraFlipped} onChange={() => { const v = !isCameraFlipped; setIsCameraFlipped(v); emit({ camera_flipped: v }); }} />
                </SectionCard>

                {/* ══════ BROWSER CONTROL ══════ */}
                <SectionCard title="Browser Control" color="cyan">
                    <div>
                        <span className="text-xs text-cyan-100/80 block mb-2">Confirmation Mode</span>
                        <div className="flex gap-1.5">
                            {['strict', 'relaxed', 'off'].map(mode => (
                                <button
                                    key={mode}
                                    onClick={() => { setConfirmationMode(mode); emit({ browser_confirmation_mode: mode }); }}
                                    className={`flex-1 py-1.5 px-2 rounded-lg text-[11px] font-medium transition-all duration-200 border ${
                                        confirmationMode === mode
                                            ? mode === 'strict' ? 'bg-red-500/15 border-red-500/40 text-red-300 shadow-[0_0_8px_rgba(239,68,68,0.1)]'
                                              : mode === 'relaxed' ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.1)]'
                                              : 'bg-yellow-500/15 border-yellow-500/40 text-yellow-300 shadow-[0_0_8px_rgba(234,179,8,0.1)]'
                                            : 'bg-black/20 border-cyan-800/30 text-cyan-600 hover:border-cyan-500/30 hover:text-cyan-400'
                                    }`}
                                >
                                    {mode.charAt(0).toUpperCase() + mode.slice(1)}
                                </button>
                            ))}
                        </div>
                        <p className="text-[10px] text-cyan-500/40 mt-2">
                            {confirmationMode === 'strict' ? 'All interactive actions require confirmation'
                             : confirmationMode === 'relaxed' ? 'Only typing & dangerous actions need confirmation'
                             : 'No confirmations except dangerous content'}
                        </p>
                    </div>
                    <button
                        onClick={() => socket.emit('kill_browser_tools')}
                        className="w-full py-2 px-3 rounded-lg text-xs font-bold bg-red-900/40 text-red-300 border border-red-700/40 hover:bg-red-800/60 hover:text-red-100 transition-all duration-200"
                    >
                        Emergency Kill — Disable All Browser Tools
                    </button>
                </SectionCard>

                {/* ══════ REMOTE CONTROL ══════ */}
                <SectionCard title="Remote Control" color="purple">
                    {remotePairing ? (
                        <div className="flex flex-col gap-3">
                            {/* QR Code */}
                            <div className="flex flex-col items-center gap-2">
                                <div className="w-[130px] h-[130px] rounded-xl border border-purple-500/30 bg-black/40 overflow-hidden flex items-center justify-center">
                                    <img
                                        src={remotePairing.qr_url}
                                        alt="Pairing QR Code"
                                        className="w-full h-full object-contain"
                                        onError={(e) => { e.target.style.display = 'none'; }}
                                    />
                                </div>
                                <p className="text-[10px] text-purple-500/60 tracking-wide text-center">Scan with phone camera</p>
                            </div>

                            {/* PIN */}
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-cyan-100/80">PIN</span>
                                <div className="flex items-center gap-2">
                                    <span className="font-mono text-base font-bold text-purple-300 tracking-[0.3em]">{remotePairing.pin}</span>
                                    <button
                                        onClick={copyPin}
                                        className="text-[10px] px-2 py-0.5 rounded border border-purple-500/30 text-purple-400 hover:bg-purple-500/10 transition-colors"
                                    >
                                        {pinCopied ? 'Copied!' : 'Copy'}
                                    </button>
                                </div>
                            </div>

                            {/* URL */}
                            <div className="flex flex-col gap-1">
                                <span className="text-xs text-cyan-100/80">LAN Address</span>
                                <div className="font-mono text-[11px] text-purple-300 bg-black/40 border border-purple-500/20 rounded-lg px-3 py-1.5 break-all select-all">
                                    {remotePairing.url}
                                </div>
                                <p className="text-[9px] text-purple-600 tracking-wide">Type this in your phone browser, then enter the PIN above</p>
                            </div>

                            {/* Buttons */}
                            <div className="flex gap-2 pt-1">
                                <button
                                    onClick={refreshPairing}
                                    className="flex-1 py-1.5 px-2 rounded-lg text-[11px] font-medium bg-purple-500/10 text-purple-400 border border-purple-500/30 hover:bg-purple-500/20 transition-all"
                                >
                                    Refresh PIN
                                </button>
                                <button
                                    onClick={revokeDevices}
                                    className="flex-1 py-1.5 px-2 rounded-lg text-[11px] font-medium bg-red-900/30 text-red-400 border border-red-700/30 hover:bg-red-800/50 transition-all"
                                >
                                    Revoke Devices
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-4">
                            <p className="text-xs text-cyan-600 mb-2">Remote pairing unavailable</p>
                            <button onClick={refreshPairing} className="text-[11px] px-3 py-1.5 rounded-lg border border-purple-500/30 text-purple-400 hover:bg-purple-500/10 transition-colors">Retry</button>
                        </div>
                    )}
                </SectionCard>

                {/* ══════ SYSTEM ══════ */}
                <SectionCard title="System" color="cyan">
                    <div>
                        <span className="text-xs text-cyan-100/80 block mb-1.5">Upload Memory Data</span>
                        <input
                            type="file"
                            accept=".txt"
                            onChange={handleFileUpload}
                            className="text-xs text-cyan-100 bg-gray-900/80 border border-cyan-800/40 rounded-lg p-2 w-full file:mr-2 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-[10px] file:font-semibold file:bg-cyan-900/60 file:text-cyan-400 hover:file:bg-cyan-800 cursor-pointer transition-colors"
                        />
                    </div>
                </SectionCard>
            </div>
        </div>
    );
};

export default SystemSettingsPanel;
