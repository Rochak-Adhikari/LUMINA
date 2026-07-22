// frontend/components/workspace/WorkspaceToolbar.jsx — header with add toggle
import React from 'react';
import { Plus, X } from 'lucide-react';
import { PageHeader } from '../ui';

export function WorkspaceToolbar({ title, subtitle, icon, addLabel, showForm, onToggleForm }) {
  return (
    <PageHeader
      title={title}
      subtitle={subtitle}
      icon={icon}
      actions={
        <button
          onClick={onToggleForm}
          className="inline-flex items-center gap-1.5 rounded-xl border border-primary-container/30 bg-primary-container/10 px-3 py-1.5 text-xs text-primary hover:bg-primary-container/20 transition-all duration-200"
        >
          {showForm ? <X size={14} /> : <Plus size={14} />}
          {showForm ? 'Cancel' : addLabel}
        </button>
      }
    />
  );
}

export default WorkspaceToolbar;
