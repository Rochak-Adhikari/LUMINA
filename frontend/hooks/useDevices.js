// frontend/hooks/useDevices.js
// Client-side media-device enumeration (mic / speaker / webcam) with selection
// persisted through the settings store (single persistence owner). Labels
// require a prior permission grant. No socket needed for enumeration; the
// selected mic id is what useVoice passes to start_audio.
import { useCallback, useEffect, useState } from 'react';
import { useSetting } from './useSetting';

function group(devices) {
  return {
    mic: devices.filter((d) => d.kind === 'audioinput'),
    speaker: devices.filter((d) => d.kind === 'audiooutput'),
    webcam: devices.filter((d) => d.kind === 'videoinput'),
  };
}

export function useDevices() {
  const [devices, setDevices] = useState({ mic: [], speaker: [], webcam: [] });

  // Selections persist via the settings store (survive restart, sync to backend).
  const [micId, setMicId] = useSetting('selected_mic_id', '');
  const [speakerId, setSpeakerId] = useSetting('selected_speaker_id', '');
  const [webcamId, setWebcamId] = useSetting('selected_webcam_id', '');

  const enumerate = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.enumerateDevices) return;
    try {
      const list = await navigator.mediaDevices.enumerateDevices();
      setDevices(group(list));
    } catch { /* enumeration denied — leave empty */ }
  }, []);

  useEffect(() => {
    enumerate();
    if (typeof navigator === 'undefined' || !navigator.mediaDevices) return undefined;
    navigator.mediaDevices.addEventListener?.('devicechange', enumerate);
    return () => navigator.mediaDevices.removeEventListener?.('devicechange', enumerate);
  }, [enumerate]);

  return {
    devices,
    micId, setMicId,
    speakerId, setSpeakerId,
    webcamId, setWebcamId,
    refresh: enumerate,
  };
}

export default useDevices;
