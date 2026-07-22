// frontend/pages/Permissions/components/PermissionBadge.jsx — colored risk badge
import React from 'react';
import { cn } from '../../../utils/cn';

const STYLES = {
  safe:         'border-green-500/30 bg-green-500/10 text-green-300',
  medium:       'border-yellow-500/30 bg-yellow-500/10 text-yellow-300',
  high:         'border-orange-500/30 bg-orange-500/10 text-orange-300',
  experimental: 'border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-300',
};
const LABELS = { safe: 'Safe', medium: 'Medium', high: 'High', experimental: 'Experimental' };

export function PermissionBadge({ risk = 'safe', className }) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider',
      STYLES[risk] || STYLES.safe, className
    )}>
      {LABELS[risk] || risk}
    </span>
  );
}

export default PermissionBadge;
