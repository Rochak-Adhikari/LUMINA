// frontend/app/routes.js — page registry (drives sidebar + CENTER content router)
// Home and Chat no longer route here: chat is merged into the always-visible
// right-hand ChatPanel (frontend/layout/ChatPanel.jsx), not a navigable page.
import {
  Home, MessageSquare, Globe, LayoutGrid, Brain, CalendarDays, ListTodo,
  Settings as SettingsIcon, Sparkles, Terminal, Activity, Info, ShieldCheck,
} from 'lucide-react';

import HomePage from '../pages/HomePage';
import ChatPage from '../pages/ChatPage';
import BrowserPage from '../pages/BrowserPage';
import WorkspacePage from '../pages/WorkspacePage';
import MemoryPage from '../pages/MemoryPage';
import SettingsPage from '../pages/SettingsPage';
import SkillsPage from '../pages/SkillsPage';
import DeveloperPage from '../pages/DeveloperPage';
import DiagnosticsPage from '../pages/DiagnosticsPage';
import AboutPage from '../pages/AboutPage';
import PermissionsPage from '../pages/PermissionsPage';

// Order = sidebar order. `group` separates primary nav from utility nav.
// `deepTab` (Calendar/Tasks) deep-links into WorkspacePage's sub-tabs instead
// of duplicating the page — see useNavStore.navigateTo / Sidebar.
export const ROUTES = [
  { id: 'home',        label: 'Home',        icon: Home,          component: HomePage,        group: 'main', noChatPanel: true },
  { id: 'chat',        label: 'Chat',        icon: MessageSquare, component: ChatPage,        group: 'main', noChatPanel: true },
  { id: 'browser',     label: 'Browser',     icon: Globe,         component: BrowserPage,     group: 'main' },
  { id: 'calendar',    label: 'Calendar',     icon: CalendarDays,  component: WorkspacePage,   group: 'main', deepTab: 'events' },
  { id: 'tasks',       label: 'Tasks',        icon: ListTodo,      component: WorkspacePage,   group: 'main', deepTab: 'quests' },
  { id: 'workspace',   label: 'Workspace',   icon: LayoutGrid,    component: WorkspacePage,   group: 'main', hidden: true },
  { id: 'memory',      label: 'Memory',      icon: Brain,         component: MemoryPage,      group: 'main' },
  { id: 'skills',      label: 'Skills',      icon: Sparkles,      component: SkillsPage,      group: 'main' },
  { id: 'permissions', label: 'Permissions', icon: ShieldCheck,   component: PermissionsPage, group: 'util' },
  { id: 'settings',    label: 'Settings',    icon: SettingsIcon,  component: SettingsPage,    group: 'util' },
  { id: 'developer',   label: 'Developer',   icon: Terminal,      component: DeveloperPage,   group: 'util' },
  { id: 'diagnostics', label: 'Diagnostics', icon: Activity,      component: DiagnosticsPage, group: 'util' },
  { id: 'about',       label: 'About',       icon: Info,          component: AboutPage,       group: 'util' },
];

// 'calendar'/'tasks'/'workspace' all render WorkspacePage; resolve any of them
// so the center panel doesn't fall back to ROUTES[0] for a valid nav target.
export const getRoute = (id) => ROUTES.find((r) => r.id === id) || ROUTES[0];
