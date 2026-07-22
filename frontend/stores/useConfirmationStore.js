// frontend/stores/useConfirmationStore.js
// Owns the pending tool-confirmation request. Session-level (a request can fire
// from any page), so state lives here and the overlay renders once in AppShell.
// No socket interaction — the useToolConfirmation hook feeds it.
import { create } from 'zustand';

export const useConfirmationStore = create((set) => ({
  request: null, // { id, tool, args } | null

  setRequest: (request) => set({ request: request || null }),
  clear: () => set({ request: null }),
}));

export default useConfirmationStore;
