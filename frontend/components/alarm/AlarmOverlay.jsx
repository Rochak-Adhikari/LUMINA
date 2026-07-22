// frontend/components/alarm/AlarmOverlay.jsx
// Presentation-only reminder-alarm modal. State/actions come from the
// useReminderAlarm hook; this component owns no socket logic. Rendered once at
// the app shell so an alarm can surface on any page.
import React from 'react';
import { AlarmClock } from 'lucide-react';
import { Dialog, Button } from '../ui';
import { useReminderAlarm } from '../../hooks/useReminderAlarm';

export function AlarmOverlay() {
  const { alarm, dismiss } = useReminderAlarm();
  if (!alarm) return null;

  return (
    <Dialog
      open
      onClose={dismiss}
      title="Reminder"
      className="border-amber-500/40"
      footer={<Button variant="primary" size="sm" onClick={dismiss}>Dismiss</Button>}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300">
          <AlarmClock size={18} />
        </div>
        <div className="min-w-0">
          <p className="text-base font-semibold text-on-surface">{alarm.title}</p>
          {alarm.notes && <p className="mt-1 text-sm text-on-surface-variant/70">{alarm.notes}</p>}
          {alarm.datetime && (
            <p className="mt-2 font-mono text-[11px] text-amber-300/70">
              {(() => { try { return new Date(alarm.datetime).toLocaleString(); } catch { return alarm.datetime; } })()}
            </p>
          )}
        </div>
      </div>
    </Dialog>
  );
}

export default AlarmOverlay;
