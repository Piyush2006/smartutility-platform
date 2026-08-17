"use client";

import { useState } from "react";
import { openAuthenticatedFile } from "@/lib/files";

/**
 * Opens an authenticated PDF endpoint in a new tab. Never use a plain
 * `<a href target="_blank">` for these -- see lib/files.ts for why that
 * 401s ("Not authenticated") instead of opening the file.
 */
export function PdfLink({ url, children, className }: { url: string; children: React.ReactNode; className?: string }) {
  const [error, setError] = useState<string | null>(null);

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={async () => {
          setError(null);
          try {
            await openAuthenticatedFile(url);
          } catch (e) {
            setError(e instanceof Error ? e.message : "Could not open file.");
          }
        }}
        className={className}
      >
        {children}
      </button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </span>
  );
}
