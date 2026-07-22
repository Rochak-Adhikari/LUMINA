// frontend/stores/useAlarmStore.js
// Owns the active reminder-alarm event. Session-level (fires from any page), so
// state lives here and the overlay renders once in AppShell. No socket
// interaction — the useReminderAlarm hook feeds it.
import { create } from 'zustand';

export const useAlarmStore = create((set) => ({
  alarm: null, // the due event object { id, title, notes?, ... } | null

  setAlarm: (alarm) => set({ alarm: alarm || null }),
  clear: () => set({ alarm: null }),
}));

export default useAlarmStore;
