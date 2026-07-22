// frontend/pages/Skills/FeatureCard.jsx — expandable capability card
import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { GlassCard } from '../../components/ui';
import { FEATURE_COLOR_MAP } from './featuresData';
import { cn } from '../../utils/cn';

export function FeatureCard({ feature }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = feature.icon;
  const c = FEATURE_COLOR_MAP[feature.color] || FEATURE_COLOR_MAP.cyan;

  return (
    <GlassCard
      hover
      onClick={() => setExpanded((e) => !e)}
      className={cn(
        'group p-4 cursor-pointer',
        expanded && cn(c.border, c.bg, 'shadow-[0_0_16px_rgba(6,182,212,0.06)]')
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-2">
        <div className={cn('shrink-0 w-9 h-9 rounded-lg border flex items-center justify-center', c.border, c.bg)}>
          <Icon size={18} className={c.icon} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-on-surface group-hover:text-white transition-colors leading-tight">
              {feature.title}
            </h3>
            <span className={cn('text-[10px] px-2 py-0.5 rounded-full border shrink-0', c.badge)}>
              {feature.badge}
            </span>
          </div>
          <p className="text-[11px] text-on-surface-variant/60 tracking-wide mt-0.5">{feature.subtitle}</p>
        </div>
        <div className="shrink-0 text-on-surface-variant/50 mt-1">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {/* Description */}
      <p className={cn('text-xs text-on-surface-variant/70 leading-relaxed', !expanded && 'line-clamp-2')}>
        {feature.description}
      </p>

      {/* Usage */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-white/5">
          <p className="text-[10px] text-primary/60 tracking-widest uppercase mb-2">How to use</p>
          <ul className="flex flex-col gap-1.5">
            {feature.usage.map((tip, i) => (
              <li key={i} className="flex items-start gap-2">
                <div className={cn('shrink-0 w-1.5 h-1.5 rounded-full mt-1.5', c.dot)} />
                <span className="text-xs text-on-surface-variant/80 leading-relaxed">{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </GlassCard>
  );
}

export default FeatureCard;
