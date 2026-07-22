// frontend/stores/useRemoteStore.js
// Owns remote-control pairing state (pushed by the backend inside the `settings`
// payload) + the last revoke result. No socket interaction — the
// useRemoteControl hook feeds it.
import { create } from 'zustand';

export const useRemoteStore = create((set) => ({
  pairing: null,       // { pin, url, qr_url, manual_url } | null
  lastRevokedCount: null,

  setPairing: (pairing) => set({ pairing: pairing || null }),
  setRevoked: (count) => set({ lastRevokedCount: count }),
}));

export default useRemoteStore;
