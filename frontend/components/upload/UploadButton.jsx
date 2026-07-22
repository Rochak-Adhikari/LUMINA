// frontend/components/upload/UploadButton.jsx
// Presentation-only file picker. Owns no socket logic — calls the provided
// onFile(file) callback (wired to useFileUpload by the page). A hidden native
// input is triggered by the icon button.
import React, { useRef } from 'react';
import { Paperclip } from 'lucide-react';
import { cn } from '../../utils/cn';

export function UploadButton({ onFile, disabled, title = 'Upload file (.txt → memory, others → AI processing)', className }) {
  const inputRef = useRef(null);

  const onChange = (e) => {
    const file = e.target.files?.[0];
    if (file) onFile(file);
    e.target.value = ''; // allow re-selecting the same file
  };

  return (
    <>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
        title={title}
        className={cn(
          'rounded-full p-2 text-on-surface-variant transition-colors hover:bg-white/10 hover:text-primary disabled:opacity-40',
          className
        )}
      >
        <Paperclip size={14} />
      </button>
      <input ref={inputRef} type="file" onChange={onChange} className="hidden" />
    </>
  );
}

export default UploadButton;
