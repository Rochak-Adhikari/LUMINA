// frontend/pages/_PagePlaceholder.jsx — shared scaffold body for placeholder pages
import React from 'react';
import { PageHeader, GlassCard } from '../components/ui';

/**
 * Placeholder page shell. States clearly that live functionality migrates here
 * in a later phase (the working feature still lives in src/Ui_TEST for now).
 */
export function PagePlaceholder({ title, subtitle, icon, migrateFrom, children }) {
  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} icon={icon} />
      {children}
      <GlassCard className="p-6 mt-2">
        <div className="flex items-center gap-2 text-xs text-primary/70 font-mono uppercase tracking-widest">
          <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse" />
          Scaffold
        </div>
        <p className="mt-2 text-sm text-on-surface-variant/80">
          This page is part of the new modular frontend architecture. Live
          functionality {migrateFrom ? `(currently in ${migrateFrom})` : ''} will
          be migrated here in the integration phase — no backend logic is wired yet.
        </p>
      </GlassCard>
    </div>
  );
}

export default PagePlaceholder;
