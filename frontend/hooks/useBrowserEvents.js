// frontend/hooks/useBrowserEvents.js
// Owns ALL Browser IPC subscriptions. Each handler is registered through the
// reference-counted ipcManager, so listeners dedup across subscribers and clean
// up automatically on unmount. Handlers are read through a ref so inline
// callbacks never cause re-subscription (reconnect/stale-safe).
import { useEffect, useRef } from 'react';
import { subscribe } from '../services/ipcManager';

// Channel -> handler-key map (main.js webContents.send channels).
const CHANNELS = {
  'browser-event-loading': 'onLoading',
  'browser-event-title': 'onTitle',
  'browser-event-favicon': 'onFavicon',
  'browser-event-navigate': 'onNavigate',
  'browser-event-new-tab': 'onNewTab',
  'browser-event-crashed': 'onCrashed',
  'browser-event-stale': 'onStale',
  'browser-event-load-error': 'onLoadError',
  'download-event-start': 'onDownloadStart',
  'download-event-update': 'onDownloadUpdate',
  'download-event-done': 'onDownloadDone',
};

export function useBrowserEvents(handlers) {
  const ref = useRef(handlers);
  ref.current = handlers;

  useEffect(() => {
    const unsubs = Object.entries(CHANNELS).map(([channel, key]) =>
      subscribe(channel, (payload) => ref.current?.[key]?.(payload))
    );
    return () => unsubs.forEach((off) => off());
  }, []);
}

export default useBrowserEvents;
