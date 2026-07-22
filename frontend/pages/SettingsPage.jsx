// frontend/pages/SettingsPage.jsx — multi-section settings, bound to the store
import React, { useMemo, useRef, useState } from 'react';
import { Settings as SettingsIcon, Download, Upload, RotateCcw } from 'lucide-react';
import { PageHeader, SettingCard, SettingGroup, Button } from '../components/ui';
import { SETTINGS_CATEGORIES } from './settings/settingsSchema';
import { SettingControl } from './settings/SettingControl';
import { SystemPanel } from './settings/SystemPanel';
import { SaveStatus } from '../components/settings/SaveStatus';
import { SettingsError } from '../components/settings/SettingsError';
import { useSettingsStore } from '../stores/useSettingsStore';
import { useSettingsStatus } from '../hooks/useSetting';
import { cn } from '../utils/cn';

export default function SettingsPage() {
  const [activeCat, setActiveCat] = useState(SETTINGS_CATEGORIES[0].id);
  const { error } = useSettingsStatus();
  const exportConfig = useSettingsStore((s) => s.exportConfig);
  const importConfig = useSettingsStore((s) => s.importConfig);
  const reset = useSettingsStore((s) => s.reset);
  const fileRef = useRef(null);

  const category = useMemo(
    () => SETTINGS_CATEGORIES.find((c) => c.id === activeCat),
    [activeCat]
  );

  const onExport = () => {
    const blob = new Blob([exportConfig()], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'lumina-settings.json'; a.click();
    URL.revokeObjectURL(url);
  };
  const onImportFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const r = new FileReader();
    r.onload = () => importConfig(String(r.result));
    r.readAsText(file);
    e.target.value = '';
  };

  return (
    <div>
      <PageHeader
        title="Settings" subtitle="Configure Lumina" icon={SettingsIcon}
        actions={
          <div className="flex items-center gap-3">
            <SaveStatus />
            <Button variant="ghost" size="sm" icon={Download} onClick={onExport}>Export</Button>
            <Button variant="ghost" size="sm" icon={Upload} onClick={() => fileRef.current?.click()}>Import</Button>
            <Button variant="outline" size="sm" icon={RotateCcw} onClick={reset}>Reset</Button>
            <input ref={fileRef} type="file" accept="application/json" className="hidden" onChange={onImportFile} />
          </div>
        }
      />

      {error ? (
        <SettingsError message={error} />
      ) : (
        <div className="flex gap-6">
          {/* Category rail */}
          <nav className="w-52 shrink-0 flex flex-col gap-1">
            {SETTINGS_CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const active = cat.id === activeCat;
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCat(cat.id)}
                  className={cn(
                    'flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-all duration-200',
                    active
                      ? 'bg-primary-container/10 border border-primary-container/40 text-primary'
                      : 'border border-transparent text-on-surface-variant hover:bg-white/5 hover:text-white'
                  )}
                >
                  <Icon size={16} className="shrink-0" />
                  <span className="truncate">{cat.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Active category — controls bind to the store internally */}
          <div className="flex-1 min-w-0 flex flex-col gap-6">
            {category.custom === 'system' ? (
              <SystemPanel />
            ) : (
              category.groups.map((group, gi) => (
                <SettingGroup key={gi} title={group.title}>
                  {group.items.map((item) => (
                    <SettingCard
                      key={item.key}
                      title={item.title}
                      description={item.description}
                      control={<SettingControl item={item} />}
                    />
                  ))}
                </SettingGroup>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
