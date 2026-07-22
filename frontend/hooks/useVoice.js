// frontend/hooks/useVoice.js
// Sole owner of the voice/audio-session socket interaction. Bridges the shared
// socket layer (Phase 5) to the voice store. Ports the audio-session logic from
// src/Ui_TEST/AppTest.jsx: mic device enumeration, start/stop/pause/resume,
// AI audio-spectrum + model-status subscriptions. No JSX, no direct socket.io.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSocket } from './useSocket';
import { useSocketEvent } from './useSocketEvent';
import { useConnectionStatus } from './useConnectionStatus';
import { useSetting } from './useSetting';
import { useVoiceStore } from '../stores/useVoiceStore';

export function useVoice() {
  const { emit, EMIT, ON } = useSocket();
  const { isConnected: socketConnected } = useConnectionStatus();

  const connected = useVoiceStore((s) => s.connected);
  const muted = useVoiceStore((s) => s.muted);
  const modelStatus = useVoiceStore((s) => s.modelStatus);
  const statusText = useVoiceStore((s) => s.statusText);
  const aiAudioData = useVoiceStore((s) => s.aiAudioData);
  const setConnected = useVoiceStore((s) => s.setConnected);
  const setMuted = useVoiceStore((s) => s.setMuted);
  const setModelStatus = useVoiceStore((s) => s.setModelStatus);
  const setStatusText = useVoiceStore((s) => s.setStatusText);
  const setAiAudioData = useVoiceStore((s) => s.setAiAudioData);

  // Mic devices (client-side enumeration; the same navigator API AppTest uses).
  // Selected mic id is persisted via the settings store — single source of truth
  // shared with the System settings panel (no duplicate device state).
  const [micDevices, setMicDevices] = useState([]);
  const [selectedMicId, setSelectedMicId] = useSetting('selected_mic_id', '');
  const hasAutoConnectedRef = useRef(false);

  // ── Backend event subscriptions (auto-cleanup, dedup, reconnect-safe) ──────
  useSocketEvent(ON.audioData, (data) => { if (data?.data) setAiAudioData(data.data); });
  useSocketEvent(ON.modelStatus, (data) => { if (data?.status) setModelStatus(data.status); });
  useSocketEvent(ON.status, (data) => {
    if (!data?.msg) return;
    if (data.msg === 'Lumina Started') setStatusText('Model Connected');
    else if (data.msg === 'Lumina Stopped') setStatusText('Connected');
  });

  // Enumerate microphones once (labels require an earlier permission grant).
  useEffect(() => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.enumerateDevices) return;
    navigator.mediaDevices.enumerateDevices().then((devs) => {
      const mics = devs.filter((d) => d.kind === 'audioinput');
      setMicDevices(mics);
      // Seed a default only when nothing is persisted yet.
      if (!selectedMicId && mics[0]?.deviceId) setSelectedMicId(mics[0].deviceId);
    }).catch(() => { /* enumeration denied — leave empty */ });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Actions ────────────────────────────────────────────────────────────────
  const start = useCallback((startMuted = true) => {
    const index = micDevices.findIndex((d) => d.deviceId === selectedMicId);
    const device = micDevices.find((d) => d.deviceId === selectedMicId);
    setStatusText('Connecting…');
    emit(EMIT.startAudio, {
      device_index: index >= 0 ? index : null,
      device_name: device ? device.label : null,
      muted: startMuted,
    });
    setConnected(true);
    setMuted(startMuted);
  }, [emit, EMIT, micDevices, selectedMicId, setConnected, setMuted, setStatusText]);

  const stop = useCallback(() => {
    emit(EMIT.stopAudio);
    setConnected(false);
    setMuted(true);
    setStatusText('Connected');
  }, [emit, EMIT, setConnected, setMuted, setStatusText]);

  const toggleMute = useCallback(() => {
    if (!connected) return;
    if (muted) { emit(EMIT.resumeAudio); setMuted(false); }
    else { emit(EMIT.pauseAudio); setMuted(true); }
  }, [connected, muted, emit, EMIT, setMuted]);

  const togglePower = useCallback(() => {
    if (connected) stop();
    else start(false);
  }, [connected, start, stop]);

  // Auto-connect once the socket is live (mirrors AppTest auto-connect).
  useEffect(() => {
    if (socketConnected && !hasAutoConnectedRef.current) {
      hasAutoConnectedRef.current = true;
      const t = setTimeout(() => start(true), 500);
      return () => clearTimeout(t);
    }
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [socketConnected]);

  return {
    // state
    connected, muted, modelStatus, statusText, aiAudioData,
    micDevices, selectedMicId, socketConnected,
    // controls
    setSelectedMicId, start, stop, toggleMute, togglePower,
  };
}

export default useVoice;
