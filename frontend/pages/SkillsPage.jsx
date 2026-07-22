// frontend/pages/SkillsPage.jsx — capability compendium (migrated FeaturesPanel)
import React, { useMemo, useState } from 'react';
import { Sparkles, Search } from 'lucide-react';
import { PageHeader, SearchBox } from '../components/ui';
import { FEATURES, FEATURE_CATEGORIES, filterFeatures } from './Skills/featuresData';
import { FeatureCard } from './Skills/FeatureCard';
import { cn } from '../utils/cn';

export default function SkillsPage() {
  const [category, setCategory] = useState('All');
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => filterFeatures(FEATURES, category, query), [category, query]);

  return (
    <div>
      <PageHeader
        title="Skills"
        subtitle={`${filtered.length} of ${FEATURES.length} capabilities · click any card for usage`}
        icon={Sparkles}
      />

      {/* Search (shared primitive) */}
      <div className="max-w-xl mx-auto mb-5">
        <SearchBox value={query} onChange={setQuery} placeholder="Search features, commands, capabilities…" />
      </div>

      {/* Category tabs */}
      <div className="flex justify-center gap-2 mb-7 flex-wrap">
        {FEATURE_CATEGORIES.map((cat) => {
          const active = category === cat;
          const count = cat === 'All' ? null : FEATURES.filter((f) => f.category === cat).length;
          return (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={cn(
                'px-3 py-1 text-xs rounded-md border transition-all duration-200',
                active
                  ? 'border-primary-container/50 bg-primary-container/10 text-primary shadow-[0_0_8px_rgba(6,182,212,0.1)]'
                  : 'border-white/10 text-on-surface-variant hover:border-primary-container/30 hover:text-primary'
              )}
            >
              {cat}
              {count != null && <span className="ml-1.5 text-[9px] text-on-surface-variant/50">{count}</span>}
            </button>
          );
        })}
      </div>

      {/* Grid */}
      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((f) => <FeatureCard key={f.id} feature={f} />)}
        </div>
      ) : (
        <div className="text-center py-16">
          <div className="w-12 h-12 rounded-full border border-white/10 flex items-center justify-center mx-auto mb-4">
            <Search size={20} className="text-on-surface-variant/50" />
          </div>
          <p className="text-on-surface-variant text-sm mb-1">No features match your search</p>
          <p className="text-on-surface-variant/50 text-xs">Try a different keyword or category.</p>
        </div>
      )}

      {/* Footer tip */}
      <div className="mt-8 pt-5 border-t border-white/5 text-center">
        <p className="text-[11px] text-on-surface-variant/50 tracking-wide">
          All actions require explicit permission in the Permissions Center before Lumina can execute them.
        </p>
      </div>
    </div>
  );
}
