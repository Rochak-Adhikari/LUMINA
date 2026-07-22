// frontend/components/workspace/ErrorToast.jsx — panel error banner
import React from 'react';

export function ErrorToast({ message }) {
  if (!message) return null;
  return (
    <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
      {message}
    </div>
  );
}

export default ErrorToast;
