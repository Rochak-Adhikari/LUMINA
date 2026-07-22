// frontend/components/layout/ResizeDivider.jsx
// Dependency-free vertical drag handle between two columns. Reports the pointer
// delta (px) to onResize; the parent applies min/max clamping + persistence.
// Uses pointer capture so the drag continues outside the handle. onResizeEnd
// fires once on release (for persisting the final width + BrowserView resync).
import React, { useCallback, useRef } from 'react';

export function ResizeDivider({ onResize, onResizeEnd }) {
  const startX = useRef(0);

  const onPointerDown = useCallback((e) => {
    startX.current = e.clientX;
    e.currentTarget.setPointerCapture(e.pointerId);
    e.preventDefault();
  }, []);

  const onPointerMove = useCallback((e) => {
    if (!e.currentTarget.hasPointerCapture?.(e.pointerId)) return;
    const dx = e.clientX - startX.current;
    if (dx !== 0) {
      startX.current = e.clientX;
      onResize(dx);
    }
  }, [onResize]);

  const onPointerUp = useCallback((e) => {
    if (e.currentTarget.hasPointerCapture?.(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    onResizeEnd?.();
  }, [onResizeEnd]);

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      className="group relative w-1.5 shrink-0 cursor-col-resize select-none"
    >
      <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-white/5 transition-colors group-hover:bg-primary-container/50" />
    </div>
  );
}

export default ResizeDivider;
