// frontend/pages/DiagnosticsPage.jsx — live system & runtime diagnostics
// Migrated from the hardcoded placeholder. All data is client-side (navigator/
// screen) via useSystemInfo — no socket, no IPC, no backend dependency.
import React from 'react';
import { Activity, Cpu, Monitor, Boxes, RefreshCw, Mic, Volume2, Camera } from 'lucide-react';
import { PageHeader, GlassCard, StatTile, Button } from '../components/ui';
import { useSystemInfo } from '../hooks/useSystemInfo';
import { fmt } from './Diagnostics/systemInfo';

function Section({ title, icon: Icon, children }) {
  return (
    <section className="mb-6">
      <div className="flex items-center gap-2 mb-3 text-xs font-bold uppercase tracking-widest text-primary/70">
        {Icon && <Icon size={13} />}
        {title}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">{children}</div>
    </section>
  );
}

export default function DiagnosticsPage() {
  const { runtime, environment, display, devices, refreshing, refresh } = useSystemInfo();

  return (
    <div>
      <PageHeader
        title="Diagnostics"
        subtitle="Runtime, environment, and device status"
        icon={Activity}
        actions={
          <Button variant="ghost" size="sm" onClick={refresh} disabled={refreshing}>
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </Button>
        }
      />

      <Section title="Runtime" icon={Boxes}>
        <StatTile label="Chromium" value={fmt(runtime.chromium)} icon={Boxes} />
        <StatTile label="Electron" value={fmt(runtime.electron)} icon={Boxes} />
        <StatTile label="Environment" value={runtime.isElectron ? 'Desktop' : 'Browser'} icon={Boxes} mono={false} />
        <StatTile label="Connectivity" value={environment.online == null ? 'Unknown' : environment.online ? 'Online' : 'Offline'} icon={Activity} mono={false} />
      </Section>

      <Section title="Host" icon={Cpu}>
        <StatTile label="Platform" value={fmt(environment.platform)} icon={Cpu} />
        <StatTile label="CPU Cores" value={fmt(environment.cores)} icon={Cpu} />
        <StatTile label="Memory" value={fmt(environment.memoryGb, ' GB')} icon={Cpu} />
        <StatTile label="Language" value={fmt(environment.language)} icon={Cpu} />
      </Section>

      <Section title="Display" icon={Monitor}>
        <StatTile label="Resolution" value={fmt(display.resolution)} icon={Monitor} />
        <StatTile label="Viewport" value={fmt(display.viewport)} icon={Monitor} />
        <StatTile label="Pixel Ratio" value={fmt(display.pixelRatio, '×')} icon={Monitor} />
        <StatTile label="Color Depth" value={fmt(display.colorDepth, '-bit')} icon={Monitor} />
      </Section>

      <Section title="Devices" icon={Mic}>
        <StatTile label="Microphones" value={devices ? devices.mic : '…'} icon={Mic} />
        <StatTile label="Speakers" value={devices ? devices.speaker : '…'} icon={Volume2} />
        <StatTile label="Webcams" value={devices ? devices.webcam : '…'} icon={Camera} />
      </Section>

      <GlassCard className="p-4">
        <p className="text-[11px] text-on-surface-variant/50 tracking-wide">
          All diagnostics are gathered locally in the renderer. Device labels
          require an active permission grant; only counts are shown here.
        </p>
      </GlassCard>
    </div>
  );
}
