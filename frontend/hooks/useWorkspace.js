// frontend/hooks/useWorkspace.js
// Domain hooks over the generic useCrudResource. Each configures event names +
// list-insertion policy to match the original Ui_TEST panels exactly.
import { useCrudResource } from './useCrudResource';
import { EMIT, ON } from '../services/socketManager';

// Quests — newest first (prepend).
export function useQuests() {
  return useCrudResource({
    panel: 'quests',
    emit: { list: EMIT.listQuests, create: EMIT.createQuest, update: EMIT.updateQuest, delete: EMIT.deleteQuest },
    on: { list: ON.questsList, created: ON.questCreated, updated: ON.questUpdated, deleted: ON.questDeleted },
  });
}

// Events — inserted then sorted ascending by datetime (matches original).
export function useEvents() {
  return useCrudResource({
    panel: 'events',
    emit: { list: EMIT.listEvents, create: EMIT.createEvent, update: EMIT.updateEvent, delete: EMIT.deleteEvent },
    on: { list: ON.eventsList, created: ON.eventCreated, updated: ON.eventUpdated, deleted: ON.eventDeleted },
    insert: (items, evt) => [...items, evt].sort((a, b) => (a.datetime || '').localeCompare(b.datetime || '')),
  });
}

// Archive notes — newest first (prepend).
export function useArchive() {
  return useCrudResource({
    panel: 'archive',
    emit: { list: EMIT.listArchiveNotes, create: EMIT.createArchiveNote, update: EMIT.updateArchiveNote, delete: EMIT.deleteArchiveNote },
    on: { list: ON.archiveNotesList, created: ON.archiveNoteCreated, updated: ON.archiveNoteUpdated, deleted: ON.archiveNoteDeleted },
  });
}
