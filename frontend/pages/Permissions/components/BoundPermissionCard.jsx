// frontend/pages/Permissions/components/BoundPermissionCard.jsx
// Store-bound wrapper: reads/writes a permission by its settingKey so each card
// rerenders only when its own value changes (Zustand selector via useSetting).
import React from 'react';
import { PermissionCard } from './PermissionCard';
import { useSetting } from '../../../hooks/useSetting';

export function BoundPermissionCard({ permission }) {
  const [value, setValue] = useSetting(permission.settingKey, permission.defaultValue);
  return (
    <PermissionCard
      permission={permission}
      enabled={!!value}
      onToggle={permission.disabled ? undefined : () => setValue(!value)}
    />
  );
}

export default BoundPermissionCard;
