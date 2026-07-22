// frontend/hooks/useProject.js
// Sole owner of project + workspace_open socket interaction. Bridges the shared
// socket layer (Phase 5) to the workspace store. Backend contract:
//   receive 'project_update'  -> { project }
//   receive 'workspace_open'  -> { type: 'browser', url }
// The nav store is switched to the browser view when a browser_open arrives so
// the embedded panel is visible. No JSX, no direct socket.io.
import { useSocket } from './useSocket';
import { useSocketEvent } from './useSocketEvent';
import { useWorkspaceStore } from '../stores/useWorkspaceStore';
import { useNavStore } from '../stores/useNavStore';

export function useProject() {
  const { ON } = useSocket();
  const project = useWorkspaceStore((s) => s.project);
  const branch = useWorkspaceStore((s) => s.branch);
  const setProject = useWorkspaceStore((s) => s.setProject);
  const requestOpen = useWorkspaceStore((s) => s.requestOpen);
  const setPage = useNavStore((s) => s.setPage);

  useSocketEvent(ON.projectUpdate, (data) => {
    if (data && data.project) setProject(data.project);
  });

  useSocketEvent(ON.workspaceOpen, (data) => {
    if (data && data.type === 'browser' && data.url) {
      requestOpen(data.url);
      setPage('browser'); // surface the embedded browser panel
    }
  });

  return { project, branch };
}

export default useProject;
