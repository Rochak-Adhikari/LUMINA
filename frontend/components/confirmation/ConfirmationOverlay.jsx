// frontend/components/confirmation/ConfirmationOverlay.jsx
// Presentation-only tool-confirmation modal. State/actions come from the
// useToolConfirmation hook; this component owns no socket logic. Rendered once
// at the app shell so it can surface on any page.
import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { Dialog, Button } from '../ui';
import { useToolConfirmation } from '../../hooks/useToolConfirmation';

export function ConfirmationOverlay() {
  const { request, confirm, deny } = useToolConfirmation();
  if (!request) return null;

  const args = request.args && typeof request.args === 'object' ? request.args : null;

  return (
    <Dialog
      open
      onClose={deny}
      title="Tool Confirmation"
      footer={(
        <>
          <Button variant="ghost" size="sm" onClick={deny}>Deny</Button>
          <Button variant="primary" size="sm" onClick={confirm}>Allow</Button>
        </>
      )}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300">
          <ShieldAlert size={18} />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-on-surface">
            Lumina wants to run <span className="font-mono text-primary">{request.tool || 'a tool'}</span>.
          </p>
          {args && (
            <pre className="mt-3 max-h-40 overflow-auto scrollbar-hide rounded-lg border border-white/10 bg-black/30 p-3 font-mono text-[11px] leading-relaxed text-on-surface-variant/80">
              {JSON.stringify(args, null, 2)}
            </pre>
          )}
          <p className="mt-3 text-xs text-on-surface-variant/60">
            Allow this action to proceed, or deny to cancel it.
          </p>
        </div>
      </div>
    </Dialog>
  );
}

export default ConfirmationOverlay;
