// frontend/hooks/useRemoteControl.js
// Sole owner of remote-control + emergency-kill socket interaction. Bridges the
// shared socket layer (Phase 5) to the remote store. Backend contract:
//   'settings' payload carries remote_pairing { pin, url, qr_url, manual_url }
//   emit 'get_settings'          -> rotates the PIN (re-broadcasts settings)
//   emit 'revoke_remote_devices' -> replies 'remote_revoked' { count }
//   emit 'kill_browser_tools'    -> disables browser perms, re-broadcasts settings
// No JSX, no direct socket.io.
import { useCallback } from 'react';
import { useSocket } from './useSocket';
import { useSocketEvent } from './useSocketEvent';
import { useRemoteStore } from '../stores/useRemoteStore';

export function useRemoteControl() {
  const { emit, EMIT, ON } = useSocket();
  const pairing = useRemoteStore((s) => s.pairing);
  const lastRevokedCount = useRemoteStore((s) => s.lastRevokedCount);
  const setPairing = useRemoteStore((s) => s.setPairing);
  const setRevoked = useRemoteStore((s) => s.setRevoked);

  // Pairing info rides along on every settings broadcast.
  useSocketEvent(ON.settings, (payload) => {
    if (payload && 'remote_pairing' in payload) setPairing(payload.remote_pairing || null);
  });
  useSocketEvent('remote_revoked', (data) => { if (data) setRevoked(data.count ?? 0); });

  // Re-requesting settings rotates the PIN on the backend.
  const refreshPairing = useCallback(() => emit(EMIT.getSettings), [emit, EMIT]);
  const revokeDevices = useCallback(() => {
    emit(EMIT.revokeRemoteDevices);
    // Refresh so the (now-rotated) PIN + empty device set come back.
    setTimeout(() => emit(EMIT.getSettings), 300);
  }, [emit, EMIT]);
  const killBrowserTools = useCallback(() => emit(EMIT.killBrowserTools), [emit, EMIT]);

  return { pairing, lastRevokedCount, refreshPairing, revokeDevices, killBrowserTools };
}

export default useRemoteControl;
