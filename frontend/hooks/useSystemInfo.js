// frontend/hooks/useSystemInfo.js
// Reads client-side runtime/environment/display/device info for the Diagnostics
// page. Synchronous facts are computed once; device counts are async (guarded
// enumerateDevices) with a manual refresh. No socket, no IPC, no persistence.
import { useCallback, useEffect, useState } from 'react';
import {
  getRuntimeInfo,
  getEnvironmentInfo,
  getDisplayInfo,
  getDeviceCounts,
} from '../pages/Diagnostics/systemInfo';

export function useSystemInfo() {
  // Synchronous snapshots — stable for the lifetime of the page.
  const [runtime] = useState(getRuntimeInfo);
  const [environment] = useState(getEnvironmentInfo);

  // Display can change (window resize / monitor move) → recompute on demand.
  const [display, setDisplay] = useState(getDisplayInfo);

  // Device counts are async and may be denied → track loading state.
  const [devices, setDevices] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setDisplay(getDisplayInfo());
    const counts = await getDeviceCounts();
    setDevices(counts);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    refresh();
    if (typeof window === 'undefined') return undefined;
    const onResize = () => setDisplay(getDisplayInfo());
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [refresh]);

  return { runtime, environment, display, devices, refreshing, refresh };
}

export default useSystemInfo;
