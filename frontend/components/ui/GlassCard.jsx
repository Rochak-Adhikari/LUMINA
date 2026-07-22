// frontend/components/ui/GlassCard.jsx — base glass surface (Lumina identity)
import React from 'react';
import { cn } from '../../utils/cn';

/**
 * Reusable frosted-glass container. Foundation for cards, panels, setting rows.
 * Variants tune elevation/glow. Preserves Lumina's futuristic aesthetic.
 */
export function GlassCard({ as: Tag = 'div', className, hover = false, glow = false, children, ...rest }) {
  return (
    <Tag
      className={cn(
        'rounded-2xl border border-white/5 bg-white/[0.03] backdrop-blur-2xl',
        hover && 'transition-all duration-300 hover:border-primary-container/30 hover:bg-white/[0.05]',
        glow && 'shadow-[0_0_40px_rgba(168,232,255,0.05)]',
        className
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
}

export default GlassCard;
