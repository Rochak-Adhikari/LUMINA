// frontend/hooks/useToolConfirmation.js
// Sole owner of tool-confirmation socket interaction. Bridges the shared socket
// layer (Phase 5) to the confirmation store. Backend contract (server.py):
//   receive 'tool_confirmation_request' -> { id, tool, args }
//   send    'confirm_tool'              -> { id, confirmed: bool }
// No JSX, no direct socket.io.
import { useCallback } from 'react';
import { useSocket } from './useSocket';
import { useSocketEvent } from './useSocketEvent';
import { useConfirmationStore } from '../stores/useConfirmationStore';

export function useToolConfirmation() {
  const { emit, EMIT, ON } = useSocket();

  const request = useConfirmationStore((s) => s.request);
  const setRequest = useConfirmationStore((s) => s.setRequest);
  const clear = useConfirmationStore((s) => s.clear);

  useSocketEvent(ON.toolConfirmationRequest, (data) => {
    if (data && data.id) setRequest(data);
  });

  const resolve = useCallback((confirmed) => {
    const current = useConfirmationStore.getState().request;
    if (!current) return;
    emit(EMIT.confirmTool, { id: current.id, confirmed });
    clear();
  }, [emit, EMIT, clear]);

  const confirm = useCallback(() => resolve(true), [resolve]);
  const deny = useCallback(() => resolve(false), [resolve]);

  return { request, confirm, deny };
}

export default useToolConfirmation;
