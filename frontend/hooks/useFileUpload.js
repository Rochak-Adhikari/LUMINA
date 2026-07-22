// frontend/hooks/useFileUpload.js
// Sole owner of file upload/processing socket interaction. Bridges the shared
// socket layer (Phase 5) to the backend. Backend contract (server.py):
//   .txt  -> emit 'upload_memory'  { memory: <text> }   (loads into model context)
//   other -> emit 'process_file'   { file_path, file_name }  (AI file analysis)
// Results return via 'status' (useVoice) and 'chat_message' (useChat) — already
// wired, so this hook is fire-and-forget. FileReader I/O lives here, not in JSX.
import { useCallback } from 'react';
import { useSocket } from './useSocket';

export function useFileUpload() {
  const { emit, EMIT } = useSocket();

  // Handle a single File (from an <input type="file"> or drop). Returns a
  // small descriptor of what was dispatched, or null if nothing was sent.
  const uploadFile = useCallback((file) => {
    if (!file) return null;
    const ext = (file.name.split('.').pop() || '').toLowerCase();

    // .txt → long-term memory ingestion.
    if (ext === 'txt') {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result;
        if (typeof text === 'string' && text.length > 0) {
          emit(EMIT.uploadMemory, { memory: text });
        }
      };
      reader.readAsText(file);
      return { kind: 'memory', name: file.name };
    }

    // Any other file → AI processing. Electron exposes an absolute path;
    // fall back to the name when running without it.
    const filePath = file.path || file.name;
    emit(EMIT.processFile, { file_path: filePath, file_name: file.name });
    return { kind: 'process', name: file.name };
  }, [emit, EMIT]);

  return { uploadFile };
}

export default useFileUpload;
