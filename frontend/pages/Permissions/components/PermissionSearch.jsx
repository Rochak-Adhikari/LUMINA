// frontend/pages/Permissions/components/PermissionSearch.jsx
// Reuses the shared SearchBox primitive; permission-scoped placeholder.
import React from 'react';
import { SearchBox } from '../../../components/ui';

export function PermissionSearch({ value, onChange }) {
  return (
    <SearchBox
      value={value}
      onChange={onChange}
      placeholder="Search permissions — browser, file, cmd…"
    />
  );
}

export default PermissionSearch;
