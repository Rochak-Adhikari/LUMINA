// frontend/hooks/useBrowser.js
// Owns ALL browser state + BrowserView lifecycle. No JSX. All IPC goes through
// useIpc (send/invoke) and useBrowserEvents (subscriptions). Ports the behavior
// of src/Ui_TEST BrowserWorkspacePanel: multi-tab create/switch/close, navigation,
// coalesced bounds sync (rAF + dedup, anti-flicker), crash/stale recovery,
// downloads, YouTube search autoplay. Presentation lives in the page/components.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useIpc } from './useIpc';
import { useBrowserEvents } from './useBrowserEvents';
import { useWorkspaceStore } from '../stores/useWorkspaceStore';

const DEFAULT_URL = 'https://www.google.com';
const newTabId = () => 'tab-' + Math.random().toString(36).slice(2, 10);

export function useBrowser(viewRef) {
  const { send, invoke, isElectron } = useIpc();

  const [tabs, setTabs] = useState([
    { id: 'tab-default', title: 'Google', url: DEFAULT_URL, loading: false, favicon: null },
  ]);
  const [activeTabId, setActiveTabId] = useState('tab-default');
  const [inputUrl, setInputUrl] = useState(DEFAULT_URL);
  const [downloads, setDownloads] = useState([]);

  // Live refs so mount-scoped recovery reads current state without stale closures.
  const tabsRef = useRef(tabs);
  const activeRef = useRef(activeTabId);
  useEffect(() => { tabsRef.current = tabs; }, [tabs]);
  useEffect(() => { activeRef.current = activeTabId; }, [activeTabId]);

  // Coalesced bounds sync: rAF + geometry dedup (anti-flicker, from the panel).
  const rafRef = useRef(0);
  const lastBoundsRef = useRef(null);
  const updateBounds = useCallback(() => {
    if (rafRef.current) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = 0;
      const el = viewRef?.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const next = {
        x: Math.round(r.left), y: Math.round(r.top),
        width: Math.round(r.width), height: Math.round(r.height), visible: true,
      };
      const p = lastBoundsRef.current;
      if (p && p.x === next.x && p.y === next.y && p.width === next.width && p.height === next.height) return;
      lastBoundsRef.current = next;
      send('browser-set-bounds', next);
    });
  }, [send, viewRef]);

  // IPC event subscriptions (auto-cleanup, dedup, reconnect-safe).
  useBrowserEvents({
    onLoading: ({ tabId, loading }) => setTabs((prev) => prev.map((t) => (t.id === tabId ? { ...t, loading } : t))),
    onTitle: ({ tabId, title }) => setTabs((prev) => prev.map((t) => (t.id === tabId ? { ...t, title } : t))),
    onFavicon: ({ tabId, favicon }) => setTabs((prev) => prev.map((t) => (t.id === tabId ? { ...t, favicon } : t))),
    onNavigate: ({ tabId, url }) => {
      setTabs((prev) => prev.map((t) => (t.id === tabId ? { ...t, url } : t)));
      if (tabId === activeRef.current) setInputUrl(url);
    },
    onNewTab: ({ url }) => createTab(url),
    onCrashed: ({ tabId }) => {
      const tab = tabsRef.current.find((t) => t.id === tabId);
      const url = tab ? tab.url : DEFAULT_URL;
      send('browser-create-tab', { tabId, url });
      if (tabId === activeRef.current) send('browser-switch-tab', { tabId });
    },
    onStale: ({ tabId, url }) => {
      send('browser-create-tab', { tabId, url });
      send('browser-switch-tab', { tabId });
      send('browser-load', { tabId, url });
    },
    onDownloadStart: (item) => setDownloads((prev) => [...prev, { ...item, progress: 0, state: 'progressing' }]),
    onDownloadUpdate: (item) => setDownloads((prev) => prev.map((d) => (d.id === item.id
      ? { ...d, state: item.state, progress: item.receivedBytes ? Math.round((item.receivedBytes / d.totalBytes) * 100) : d.progress } : d))),
    onDownloadDone: (item) => setDownloads((prev) => prev.map((d) => (d.id === item.id ? { ...d, state: item.state, progress: 100 } : d))),
  });

  // Mount: create the initial BrowserView(s), attach resize/observer bounds sync.
  useEffect(() => {
    if (!isElectron) return undefined;
    tabsRef.current.forEach((t) => send('browser-create-tab', { tabId: t.id, url: t.url }));
    send('browser-switch-tab', { tabId: activeRef.current });

    let observer;
    if (viewRef?.current) {
      observer = new ResizeObserver(() => updateBounds());
      observer.observe(viewRef.current);
    }
    window.addEventListener('resize', updateBounds);
    const timers = [100, 300, 600].map((ms) => setTimeout(updateBounds, ms));

    return () => {
      window.removeEventListener('resize', updateBounds);
      if (observer) observer.disconnect();
      timers.forEach(clearTimeout);
      if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = 0; }
      lastBoundsRef.current = null;
      send('browser-set-bounds', { visible: false });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isElectron]);

  // Switch active tab: notify main + resync bounds.
  useEffect(() => {
    const tab = tabs.find((t) => t.id === activeTabId);
    if (!tab) return;
    setInputUrl(tab.url);
    send('browser-switch-tab', { tabId: activeTabId });
    const t = setTimeout(updateBounds, 80);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTabId]);

  // ── Actions ──────────────────────────────────────────────────────────────
  const createTab = useCallback((url = DEFAULT_URL) => {
    const id = newTabId();
    setTabs((prev) => [...prev, { id, title: 'New Tab', url, loading: false, favicon: null }]);
    send('browser-create-tab', { tabId: id, url });
    setActiveTabId(id);
  }, [send]);

  const closeTab = useCallback((tabId) => {
    setTabs((prev) => {
      if (prev.length === 1) return prev;
      const index = prev.findIndex((t) => t.id === tabId);
      const filtered = prev.filter((t) => t.id !== tabId);
      send('browser-close-tab', { tabId });
      if (activeRef.current === tabId) {
        const nextTab = filtered[index - 1] || filtered[0];
        if (nextTab) setActiveTabId(nextTab.id);
      }
      return filtered;
    });
  }, [send]);

  const switchTab = useCallback((tabId) => setActiveTabId(tabId), []);

  const navigate = useCallback((url) => {
    const target = (url ?? inputUrl).trim();
    if (!target) return;
    // YouTube search URLs → in-view playback automation (wait→click→play→unmute).
    const yt = /youtube\.com\/results\?search_query=([^&]+)/i.exec(target);
    if (yt && isElectron) {
      const query = decodeURIComponent(yt[1].replace(/\+/g, ' '));
      invoke('browser-youtube-play', { tabId: activeRef.current, query })
        .catch(() => send('browser-load', { tabId: activeRef.current, url: target }));
    } else {
      send('browser-load', { tabId: activeRef.current, url: target });
    }
    setTimeout(updateBounds, 80);
  }, [inputUrl, isElectron, invoke, send, updateBounds]);

  const reload = useCallback(() => send('browser-reload', { tabId: activeRef.current }), [send]);
  const back = useCallback(() => send('browser-go-back', { tabId: activeRef.current }), [send]);
  const forward = useCallback(() => send('browser-go-forward', { tabId: activeRef.current }), [send]);
  const toggleDevtools = useCallback(() => send('browser-devtools', { tabId: activeRef.current }), [send]);
  const executeJS = useCallback((code) => invoke('browser-execute-js', { tabId: activeRef.current, code }), [invoke]);
  const setViewVisible = useCallback((visible) => send('browser-set-visible', { visible }), [send]);

  // Backend-pushed browser opens ('workspace_open' → workspace store). When the
  // request timestamp changes, load the URL into the active tab. Keyed on ts so
  // repeated opens of the same URL still navigate.
  const openRequest = useWorkspaceStore((s) => s.openRequest);
  useEffect(() => {
    if (!openRequest || !openRequest.url) return;
    setInputUrl(openRequest.url);
    navigate(openRequest.url);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openRequest?.ts]);

  const activeTab = tabs.find((t) => t.id === activeTabId) || null;

  return {
    // state
    tabs, activeTab, activeTabId, url: inputUrl, downloads,
    loading: !!activeTab?.loading,
    isElectron,
    // input control
    setInputUrl,
    // actions
    createTab, closeTab, switchTab, navigate, reload, back, forward,
    executeJS, toggleDevtools, updateBounds, setViewVisible,
  };
}

export default useBrowser;
