// frontend/components/workspace/FilterTabs.jsx — pill tab bar with counts
import React from 'react';
import { cn } from '../../utils/cn';

export function FilterTabs({ tabs, active, onChange }) {
  return (
    <div className="mb-6 flex flex-wrap justify-center gap-2">
      {tabs.map((tab) => {
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'rounded-md border px-3 py-1 text-xs transition-all duration-200',
              isActive
                ? 'border-primary-container/50 bg-primary-container/10 text-primary shadow-[0_0_8px_rgba(6,182,212,0.1)]'
                : 'border-white/10 text-on-surface-variant hover:border-primary-container/30 hover:text-primary'
            )}
          >
            {tab.label}
            {typeof tab.count === 'number' && (
              <span className="ml-1.5 text-[9px] text-on-surface-variant/50">{tab.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default FilterTabs;
