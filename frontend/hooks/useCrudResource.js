// frontend/hooks/useCrudResource.js
// Generic socket-CRUD resource. Parameterized by a config of event names, it
// owns the list state and keeps it in sync with server broadcasts (list /
// created / updated / deleted) plus the shared `panel_error` channel. All
// socket interaction goes through the Phase-5 layer (useSocket/useSocketEvent):
// no page owns socket logic, no direct socket.io.
//
// config = {
//   panel,                       // 'quests' | 'events' | 'archive'
//   emit:  { list, create, update, delete },   // EMIT event names
//   on:    { list, created, updated, deleted }, // ON event names
//   insert,                      // (items, item) => items   (placement policy)
//   errorMs,                     // toast auto-clear (default 4000)
// }
import { useCallback, useEffect, useState } from 'react';
import { useSocket } from './useSocket';
import { useSocketEvent } from './useSocketEvent';
import { ON } from '../services/socketManager';

const prepend = (items, item) => [item, ...items];

export function useCrudResource(config) {
  const { panel, emit: emitEvents, on: onEvents, insert = prepend, errorMs = 4000 } = config;
  const { emit } = useSocket();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initial fetch (and re-fetch on reconnect via the `connect` event).
  const refetch = useCallback(() => {
    setLoading(true);
    emit(emitEvents.list);
  }, [emit, emitEvents.list]);

  useEffect(() => { refetch(); }, [refetch]);
  useSocketEvent('connect', refetch); // reconnect-safe re-fetch

  useSocketEvent(onEvents.list, (data) => {
    setItems(Array.isArray(data) ? data : []);
    setLoading(false);
  });
  useSocketEvent(onEvents.created, (item) => {
    if (item) setItems((prev) => insert(prev, item));
  });
  useSocketEvent(onEvents.updated, (item) => {
    if (item) setItems((prev) => prev.map((x) => (x.id === item.id ? item : x)));
  });
  useSocketEvent(onEvents.deleted, (data) => {
    if (data) setItems((prev) => prev.filter((x) => x.id !== data.id));
  });

  // Shared error channel, filtered by panel.
  useSocketEvent(ON.panelError, (data) => {
    if (data && data.panel === panel) {
      setError(data.error);
      setTimeout(() => setError(null), errorMs);
    }
  });

  const create = useCallback((payload) => emit(emitEvents.create, payload), [emit, emitEvents.create]);
  const update = useCallback((payload) => emit(emitEvents.update, payload), [emit, emitEvents.update]);
  const remove = useCallback((id) => emit(emitEvents.delete, { id }), [emit, emitEvents.delete]);

  return { items, loading, error, create, update, remove, refetch };
}

export default useCrudResource;
