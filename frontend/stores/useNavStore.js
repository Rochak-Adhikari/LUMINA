// frontend/stores/useNavStore.js — single source of truth for active page + sidebar
import { create } from 'zustand';

export const useNavStore = create((set) => ({
  activePage: 'home',
  sidebarCollapsed: false,
  search: '',
  workspaceTab: null, // optional deep-link target for the Workspace sub-tabs
  setPage: (page) => set((s) => (s.activePage === page ? s : { activePage: page })),
  // Navigate to a page and (optionally) a sub-view in one atomic update.
  navigateTo: (page, workspaceTab = null) =>
    set((s) => (s.activePage === page && s.workspaceTab === workspaceTab
      ? s
      : { activePage: page, workspaceTab })),
  setWorkspaceTab: (workspaceTab) => set({ workspaceTab }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSearch: (search) => set({ search }),
}));

export default useNavStore;
