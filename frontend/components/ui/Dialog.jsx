// frontend/components/ui/Dialog.jsx — modal overlay (highest z, glass)
import React from 'react';
import { X } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { cn } from '../../utils/cn';

export function Dialog({ open, onClose, title, children, footer, className }) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <GlassCard
        glow
        className={cn('relative w-[440px] max-w-[90vw] p-6', className)}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-sora text-lg font-semibold text-primary">{title}</h2>
          <button onClick={onClose} className="text-on-surface-variant hover:text-red-400 transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="text-sm text-on-surface">{children}</div>
        {footer && <div className="mt-6 flex justify-end gap-3">{footer}</div>}
      </GlassCard>
    </div>
  );
}

export default Dialog;
