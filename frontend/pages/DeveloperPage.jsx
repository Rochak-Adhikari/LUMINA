import React from 'react';
import { Terminal } from 'lucide-react';
import { PagePlaceholder } from './_PagePlaceholder';

export default function DeveloperPage() {
  return (
    <PagePlaceholder title="Developer" subtitle="Logs, IPC console, tool inspector" icon={Terminal} migrateFrom="electron main + backend logs" />
  );
}
