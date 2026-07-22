// frontend/hooks/useSocketEvent.js
// Subscribe to one server event for the component's lifetime. Listener is
// registered via the reference-counted manager and auto-removed on unmount or
// when the event changes. The latest handler is always called without
// re-subscribing (ref indirection), so inline callbacks are safe.
import { useEffect, useRef } from 'react';
import { subscribe } from '../services/socketManager';

export function useSocketEvent(event, handler, { enabled = true } = {}) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    if (!enabled || !event) return undefined;
    const unsubscribe = subscribe(event, (...args) => handlerRef.current?.(...args));
    return unsubscribe;
  }, [event, enabled]);
}

export default useSocketEvent;
