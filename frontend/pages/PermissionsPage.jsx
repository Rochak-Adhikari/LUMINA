// frontend/pages/PermissionsPage.jsx — dedicated Permissions Center (store-bound)
// Every permission reads/writes through the settings store by its settingKey.
// Overview counts derive from the store. NO local permission state.
import React, { useMemo, useState } from 'react';
import { ShieldCheck, CheckCircle, XCircle, AlertTriangle, Gauge } from 'lucide-react';
import { PageHeader } from '../components/ui';
import {
  PERMISSION_CATEGORIES, PERMISSIONS,
  permissionsForCategory, filterPermissions,
} from './Permissions/permissionsSchema';
import {
  BoundPermissionCard, PermissionCategory, PermissionSearch, PermissionOverviewCard,
} from './Permissions/components';
import { SaveStatus } from '../components/settings/SaveStatus';
import { SettingsError } from '../components/settings/SettingsError';
import { useSettingsStore } from '../stores/useSettingsStore';
import { useSettingsStatus } from '../hooks/useSetting';
import { getPath } from '../utils/paths';

export default function PermissionsPage() {
  const [activeCat, setActiveCat] = useState('security');
  const [search, setSearch] = useState('');
  const { error } = useSettingsStatus();

  // Subscribe to the settings object (stable ref) and derive counts in a memo.
  // Returning a fresh object straight from the selector would make
  // useSyncExternalStore loop ("getSnapshot should be cached").
  const cfg = useSettingsStore((s) => s.settings);
  const overview = useMemo(() => {
    const total = PERMISSIONS.length;
    const on = PERMISSIONS.filter((p) => getPath(cfg, p.settingKey, p.defaultValue)).length;
    const high = PERMISSIONS.filter(
      (p) => (p.risk === 'high' || p.risk === 'experimental') && getPath(cfg, p.settingKey, p.defaultValue)
    ).length;
    const level = high >= 3 ? 'Permissive' : high >= 1 ? 'Balanced' : 'Locked Down';
    return { on, off: total - on, high, level };
  }, [cfg]);

  const searching = search.trim().length > 0;
  const shown = searching ? filterPermissions(search) : permissionsForCategory(activeCat);
  const activeCategory = PERMISSION_CATEGORIES.find((c) => c.id === activeCat);
  const showOverview = !searching && activeCategory?.overview;

  return (
    <div>
      <PageHeader
        title="Permissions Center" subtitle="Manage what Lumina is allowed to do" icon={ShieldCheck}
        actions={<SaveStatus />}
      />

      {error ? (
        <SettingsError message={error} />
      ) : (
        <div className="flex gap-6">
          {/* LEFT: category rail */}
          <nav className="w-56 shrink-0 flex flex-col gap-1">
            {PERMISSION_CATEGORIES.map((cat) => (
              <PermissionCategory
                key={cat.id}
                category={cat}
                active={!searching && cat.id === activeCat}
                onClick={() => { setSearch(''); setActiveCat(cat.id); }}
                count={cat.overview ? undefined : permissionsForCategory(cat.id).length}
              />
            ))}
          </nav>

          {/* RIGHT: search + overview/cards */}
          <div className="flex-1 min-w-0 flex flex-col gap-5">
            <PermissionSearch value={search} onChange={setSearch} />

            {showOverview && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <PermissionOverviewCard label="Enabled"        value={overview.on}    tone="green"   icon={CheckCircle} />
                <PermissionOverviewCard label="Disabled"       value={overview.off}   tone="neutral" icon={XCircle} />
                <PermissionOverviewCard label="High Risk"      value={overview.high}  tone="orange"  icon={AlertTriangle} />
                <PermissionOverviewCard label="Security Level" value={overview.level} tone="primary" icon={Gauge} />
              </div>
            )}

            {!showOverview && (
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-widest text-primary/70">
                  {searching ? `Results for “${search}”` : activeCategory?.label}
                </h3>
                <span className="text-[10px] font-mono text-on-surface-variant/50">{shown.length} permissions</span>
              </div>
            )}

            {!showOverview && (
              <div className="flex flex-col gap-3">
                {shown.length === 0 ? (
                  <div className="rounded-xl border border-white/5 bg-white/[0.02] p-8 text-center text-sm text-on-surface-variant/60">
                    No permissions match your search.
                  </div>
                ) : (
                  shown.map((p) => <BoundPermissionCard key={p.settingKey} permission={p} />)
                )}
              </div>
            )}

            {showOverview && (
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5 text-xs text-on-surface-variant/70">
                Select a category on the left to review individual permissions, or
                search above to filter across all categories. Changes persist
                automatically (local store).
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
