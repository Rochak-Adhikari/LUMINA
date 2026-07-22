// frontend/pages/AboutPage.jsx — static app identity, stack, capability pillars
// Fully client-side static content. No socket, no IPC, no backend, no storage.
import React from 'react';
import { Info, ArrowRight } from 'lucide-react';
import { PageHeader, GlassCard, StatTile } from '../components/ui';
import { useNavStore } from '../stores/useNavStore';
import { APP, STACK, PILLARS, LINKS } from './About/aboutData';

export default function AboutPage() {
  const setPage = useNavStore((s) => s.setPage);

  return (
    <div>
      <PageHeader title="About" subtitle="Lumina AI desktop assistant" icon={Info} />

      {/* Identity */}
      <GlassCard glow className="p-6 mb-6">
        <div className="font-sora text-3xl font-semibold text-primary">{APP.name}</div>
        <div className="mt-1 text-sm text-on-surface-variant">{APP.tagline}</div>
        <div className="mt-1 text-xs font-mono text-primary/60">v{APP.version}</div>
        <p className="mt-4 max-w-2xl text-sm text-on-surface-variant/80 leading-relaxed">
          {APP.description}
        </p>
      </GlassCard>

      {/* Stack */}
      <div className="mb-2 text-xs font-bold uppercase tracking-widest text-primary/70">Technology</div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        {STACK.map((s) => (
          <StatTile key={s.label} label={s.label} value={s.value} mono={false} />
        ))}
      </div>

      {/* Pillars */}
      <div className="mb-2 text-xs font-bold uppercase tracking-widest text-primary/70">Capabilities</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {PILLARS.map((p) => (
          <GlassCard key={p.title} hover className="p-5">
            <h3 className="text-sm font-semibold text-on-surface">{p.title}</h3>
            <p className="mt-1.5 text-xs text-on-surface-variant/70 leading-relaxed">{p.text}</p>
          </GlassCard>
        ))}
      </div>

      {/* Links */}
      <div className="flex flex-wrap gap-3">
        {LINKS.map((l) => (
          <button
            key={l.page}
            onClick={() => setPage(l.page)}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-xs text-on-surface-variant hover:border-primary-container/40 hover:text-primary transition-all duration-200"
          >
            {l.label}
            <ArrowRight size={13} />
          </button>
        ))}
      </div>
    </div>
  );
}
