// frontend/hooks/useReminderAlarm.js
// Sole owner of reminder-alarm socket interaction. Bridges the shared socket
// layer (Phase 5) to the alarm store. Backend contract (server.py):
//   receive 'reminder_alarm'           -> event object { id, title, notes?, ... }
//   send    'reminder_alarm_dismissed' -> { event_id, title, dismissed_at_iso }
// On dismiss the backend marks the event completed and routes a Gemini
// follow-up. Plays a short chime and auto-dismisses after 15s (mirrors the
// reference behavior). No JSX, no direct socket.io.
import { useCallback, useEffect, useRef } from 'react';
import { useSocket } from './useSocket';
import { useSocketEvent } from './useSocketEvent';
import { useAlarmStore } from '../stores/useAlarmStore';

const AUTO_DISMISS_MS = 15000;

function playChime() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.frequency.value = 880; osc.type = 'sine'; gain.gain.value = 0.3;
    osc.start();
    [200, 400, 600, 800].forEach((t, i) => setTimeout(() => { gain.gain.value = i % 2 === 0 ? 0 : 0.3; }, t));
    setTimeout(() => { gain.gain.value = 0; osc.stop(); ctx.close(); }, 1000);
  } catch { /* audio unavailable — non-fatal */ }
}

export function useReminderAlarm() {
  const { emit, EMIT, ON } = useSocket();
  const alarm = useAlarmStore((s) => s.alarm);
  const setAlarm = useAlarmStore((s) => s.setAlarm);
  const clear = useAlarmStore((s) => s.clear);
  const timerRef = useRef(null);

  const dismiss = useCallback(() => {
    const current = useAlarmStore.getState().alarm;
    if (!current) return;
    emit(EMIT.reminderAlarmDismissed, {
      event_id: current.id,
      title: current.title,
      dismissed_at_iso: new Date().toISOString(),
    });
    clear();
  }, [emit, EMIT, clear]);

  useSocketEvent(ON.reminderAlarm, (evt) => {
    if (evt && evt.id != null) { setAlarm(evt); playChime(); }
  });

  // Auto-dismiss after 15s (also fires the dismissed follow-up via dismiss()).
  useEffect(() => {
    if (!alarm) return undefined;
    timerRef.current = setTimeout(() => dismiss(), AUTO_DISMISS_MS);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [alarm, dismiss]);

  return { alarm, dismiss };
}

export default useReminderAlarm;
