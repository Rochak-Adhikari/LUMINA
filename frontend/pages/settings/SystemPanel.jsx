// frontend/pages/settings/SystemPanel.jsx
// Presentation-only System panel: media-device selection + remote-control
// pairing + emergency browser-tool kill. All backend/socket logic lives in
// useDevices / useRemoteControl. Rendered as a Settings category.
import React, { useState } from 'react';
import { Mic, Volume2, Camera, RefreshCw, Copy, ShieldOff } from 'lucide-react';
import { GlassCard, Select, Button } from '../../components/ui';
import { SettingGroup } from '../../components/ui';
import { useDevices } from '../../hooks/useDevices';
import { useRemoteControl } from '../../hooks/useRemoteControl';

function deviceOptions(list, fallbackLabel) {
  return list.map((d, i) => ({ value: d.deviceId, label: d.label || `${fallbackLabel} ${i + 1}` }));
}

export function SystemPanel() {
  const dev = useDevices();
  const remote = useRemoteControl();
  const [copied, setCopied] = useState(false);

  const copyPin = () => {
    const pin = remote.pairing?.pin;
    if (!pin || !navigator.clipboard) return;
    navigator.clipboard.writeText(pin).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* ── Devices ── */}
      <SettingGroup title="Devices">
        <GlassCard className="p-5 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="flex items-center gap-1.5 text-xs text-on-surface-variant"><Mic size={13} /> Microphone</span>
            <Select value={dev.micId} onChange={dev.setMicId} options={deviceOptions(dev.devices.mic, 'Microphone')} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="flex items-center gap-1.5 text-xs text-on-surface-variant"><Volume2 size={13} /> Speaker</span>
            <Select value={dev.speakerId} onChange={dev.setSpeakerId} options={deviceOptions(dev.devices.speaker, 'Speaker')} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="flex items-center gap-1.5 text-xs text-on-surface-variant"><Camera size={13} /> Webcam</span>
            <Select value={dev.webcamId} onChange={dev.setWebcamId} options={deviceOptions(dev.devices.webcam, 'Camera')} />
          </label>
          <Button variant="ghost" size="sm" icon={RefreshCw} onClick={dev.refresh} className="self-start">Refresh devices</Button>
        </GlassCard>
      </SettingGroup>

      {/* ── Remote control ── */}
      <SettingGroup title="Remote Control">
        <GlassCard className="p-5">
          {remote.pairing ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-4">
                {remote.pairing.qr_url && (
                  <img src={remote.pairing.qr_url} alt="Pairing QR" className="h-[130px] w-[130px] rounded-xl border border-primary-container/30 bg-black/40 object-contain"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                )}
                <div className="flex flex-col gap-2 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-on-surface-variant">PIN</span>
                    <span className="font-mono text-base font-bold tracking-[0.3em] text-primary">{remote.pairing.pin}</span>
                    <button onClick={copyPin} className="inline-flex items-center gap-1 rounded border border-primary-container/30 px-2 py-0.5 text-[10px] text-primary hover:bg-primary-container/10">
                      <Copy size={10} />{copied ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  {remote.pairing.url && (
                    <div className="font-mono text-[11px] text-primary/80 break-all select-all rounded-lg border border-primary-container/20 bg-black/40 px-3 py-1.5">
                      {remote.pairing.url}
                    </div>
                  )}
                  <p className="text-[10px] text-on-surface-variant/50">Scan the QR or open the URL on your phone, then enter the PIN.</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" icon={RefreshCw} onClick={remote.refreshPairing}>Refresh PIN</Button>
                <Button variant="danger" size="sm" onClick={remote.revokeDevices}>Revoke devices</Button>
              </div>
              {remote.lastRevokedCount != null && (
                <p className="text-[10px] text-on-surface-variant/50">Revoked {remote.lastRevokedCount} device(s).</p>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-between gap-4">
              <p className="text-xs text-on-surface-variant/60">Remote pairing unavailable. Refresh to request a pairing code.</p>
              <Button variant="ghost" size="sm" icon={RefreshCw} onClick={remote.refreshPairing}>Retry</Button>
            </div>
          )}
        </GlassCard>
      </SettingGroup>

      {/* ── Emergency ── */}
      <SettingGroup title="Emergency">
        <GlassCard className="p-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm text-on-surface">Kill all browser tools</p>
            <p className="text-xs text-on-surface-variant/60">Instantly disable browser automation for this session.</p>
          </div>
          <Button variant="danger" size="sm" icon={ShieldOff} onClick={remote.killBrowserTools}>Kill browser tools</Button>
        </GlassCard>
      </SettingGroup>
    </div>
  );
}

export default SystemPanel;
