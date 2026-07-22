// frontend/pages/settings/SettingControl.jsx — self-binding control (store-backed)
// Each control subscribes to ONLY its own path via useSetting, so editing one
// setting does not rerender the others.
import React from 'react';
import { Toggle, Slider, Select } from '../../components/ui';
import { useSetting } from '../../hooks/useSetting';

export function SettingControl({ item }) {
  const scale = item.scale || 1;
  const [stored, setStored] = useSetting(item.path);

  switch (item.type) {
    case 'toggle':
      return <Toggle checked={!!stored} onChange={setStored} />;

    case 'slider': {
      // stored value may be scaled (e.g. 0–1 persisted, shown as 0–100 %)
      const shown = scale === 1 ? (stored ?? item.min) : Math.round((stored ?? 0) * scale);
      return (
        <Slider
          value={shown} min={item.min} max={item.max} step={item.step || 1} suffix={item.suffix || ''}
          onChange={(v) => setStored(scale === 1 ? v : v / scale)}
          className="w-48"
        />
      );
    }

    case 'select':
      return (
        <Select
          value={stored ?? (item.options && item.options[0])}
          options={item.options || []}
          onChange={setStored}
          className="w-52"
        />
      );

    default:
      return <span className="text-xs text-on-surface-variant/40">—</span>;
  }
}

export default SettingControl;
