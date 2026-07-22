// frontend/stores/useWorkspaceStore.js
// Owns cross-cutting workspace session state:
//   - current project (pushed by backend 'project_update')
//   - a backend-requested browser URL (pushed by 'workspace_open'), carried with
//     a timestamp so repeated opens of the same URL still trigger navigation.
// No socket interaction — the useProject / useWorkspaceBrowser hooks feed it.
import { create } from 'zustand';

export const useWorkspaceStore = create((set) => ({
  project: 'default',
  branch: 'main',
  openRequest: null, // { url, ts } | null — latest backend browser_open

  setProject: (project, branch = 'main') => set({ project: project || 'default', branch }),
  requestOpen: (url) => set({ openRequest: { url, ts: Date.now() } }),
  clearOpen: () => set({ openRequest: null }),
}));

export default useWorkspaceStore;
