// frontend/pages/Permissions/components/PermissionToggle.jsx
// Thin wrapper over the shared Toggle primitive so permission-specific styling
// stays in one place (no duplicated toggle logic).
import React from 'react';
import { Toggle } from '../../../components/ui';

export function PermissionToggle({ enabled, onChange, disabled }) {
  return <Toggle checked={!!enabled} onChange={onChange} disabled={disabled} />;
}

export default PermissionToggle;
